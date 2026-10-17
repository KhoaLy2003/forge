package {{ base_package }}.notification;

import {{ base_package }}.common.dto.PageResponse;
import {{ base_package }}.common.exception.ResourceNotFoundException;
import {{ base_package }}.common.util.PaginationUtils;
import {{ base_package }}.notification.dto.InboxItemResponse;
import {{ base_package }}.notification.dto.PreferencesResponse;
import {{ base_package }}.notification.dto.UpdatePreferencesRequest;
import {{ base_package }}.notification.entity.NotificationPreference;
import {{ base_package }}.notification.entity.NotificationTemplate;
import {{ base_package }}.notification.repository.NotificationPreferenceRepository;
import {{ base_package }}.notification.repository.NotificationTemplateRepository;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.UUID;
import java.util.stream.Collectors;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Default implementation of {@link NotificationService}. Read-only by default; mutating methods opt
 * in to a writable transaction.
 */
@Service
@RequiredArgsConstructor
@Slf4j
@Transactional(readOnly = true)
public class NotificationServiceImpl implements NotificationService {

  /** Largest explicit audience accepted in one request. */
  public static final int MAX_EXPLICIT_RECIPIENTS = 500;

  private final NotificationQueries queries;
  private final NotificationTemplateRepository templateRepository;
  private final NotificationPreferenceRepository preferenceRepository;

  /** {@inheritDoc} */
  @Override
  @Transactional
  public NotificationAck enqueue(NotificationRequest request) {
    validate(request);
    Map<String, String> data = request.data() == null ? Map.of() : request.data();
    boolean dueNow = request.scheduledAt() == null || !request.scheduledAt().isAfter(Instant.now());
    String status = dueNow ? NotificationStatus.QUEUED : NotificationStatus.ACCEPTED;
    List<String> channels =
        request.channels().stream().sorted().map(NotificationChannel::dbValue).toList();

    NotificationQueries.Inserted inserted =
        queries
            .insertNotification(
                request.type(),
                request.templateKey(),
                String.join(",", channels),
                request.audience().type(),
                data,
                status,
                request.scheduledAt(),
                request.idempotencyKey(),
                request.createdBy())
            .orElse(null);
    if (inserted == null) {
      NotificationQueries.Existing existing =
          queries
              .findByIdempotencyKey(request.idempotencyKey())
              .orElseThrow(
                  () -> new IllegalStateException("Idempotency conflict without existing row"));
      return new NotificationAck(existing.id(), existing.status(), existing.createdAt(), true);
    }
    queries.insertDeliveries(
        inserted.id(), request.audience().userIds(), channels, request.scheduledAt());
    // No template data and no recipient ids: both can be personal data.
    log.atInfo()
        .addKeyValue("event.name", "notification.accepted")
        .addKeyValue("notification.id", inserted.id())
        .addKeyValue("notification.type", request.type())
        .addKeyValue("notification.status", status)
        .log("Notification accepted");
    return new NotificationAck(inserted.id(), status, inserted.createdAt(), false);
  }

  /** {@inheritDoc} */
  @Override
  public PageResponse<InboxItemResponse> inbox(UUID recipientId, int page, int size) {
    Pageable pageable = PaginationUtils.createPageable(page, size, "createdAt", "DESC");
    List<InboxItemResponse> items =
        queries.inbox(recipientId, size, (long) page * size).stream()
            .map(
                row ->
                    new InboxItemResponse(
                        row.id(),
                        row.notificationId(),
                        row.type(),
                        row.title(),
                        row.body(),
                        row.createdAt(),
                        row.read()))
            .toList();
    return PaginationUtils.toPageResponse(
        new PageImpl<>(items, pageable, queries.inboxCount(recipientId)), items);
  }

  /** {@inheritDoc} */
  @Override
  public long unreadCount(UUID recipientId) {
    return queries.unreadCount(recipientId);
  }

  /** {@inheritDoc} */
  @Override
  @Transactional
  public void markRead(UUID recipientId, UUID deliveryId) {
    if (!queries.markRead(deliveryId, recipientId)) {
      throw new ResourceNotFoundException("Notification not found: " + deliveryId);
    }
  }

  /** {@inheritDoc} */
  @Override
  @Transactional
  public void markAllRead(UUID recipientId) {
    queries.markAllRead(recipientId);
  }

  /** {@inheritDoc} */
  @Override
  @Transactional
  public void deleteNotification(UUID recipientId, UUID deliveryId) {
    if (!queries.dismiss(deliveryId, recipientId)) {
      throw new ResourceNotFoundException("Notification not found: " + deliveryId);
    }
  }

  /** {@inheritDoc} */
  @Override
  public PreferencesResponse getPreferences(UUID recipientId) {
    return preferenceRepository
        .findByRecipientIdAndDeletedAtIsNull(recipientId)
        .map(preference -> new PreferencesResponse(preference.isEmailEnabled()))
        .orElseGet(() -> new PreferencesResponse(true));
  }

  /** {@inheritDoc} */
  @Override
  @Transactional
  public PreferencesResponse updatePreferences(UUID recipientId, UpdatePreferencesRequest request) {
    NotificationPreference preference =
        preferenceRepository
            .findByRecipientIdAndDeletedAtIsNull(recipientId)
            .orElseGet(() -> NotificationPreference.builder().recipientId(recipientId).build());
    if (request.emailEnabled() != null) {
      preference.setEmailEnabled(request.emailEnabled());
    }
    NotificationPreference saved = preferenceRepository.save(preference);
    return new PreferencesResponse(saved.isEmailEnabled());
  }

  /** {@inheritDoc} */
  @Override
  @Transactional
  public void purgeRecipient(UUID recipientId) {
    queries.deleteDeliveriesOf(recipientId);
    preferenceRepository.deleteByRecipientId(recipientId);
  }

  private void validate(NotificationRequest request) {
    if (request.channels() == null || request.channels().isEmpty()) {
      throw new IllegalArgumentException("At least one channel is required");
    }
    Audience audience = request.audience();
    if (audience == null) {
      throw new IllegalArgumentException("An audience is required");
    }
    if (audience.userIds().isEmpty() || audience.userIds().size() > MAX_EXPLICIT_RECIPIENTS) {
      throw new IllegalArgumentException(
          "Between 1 and " + MAX_EXPLICIT_RECIPIENTS + " recipients required");
    }
    List<NotificationTemplate> templates =
        templateRepository.findByTemplateKeyAndActiveTrueAndDeletedAtIsNull(request.templateKey());
    Set<String> required = new TreeSet<>();
    for (NotificationChannel channel : request.channels()) {
      List<NotificationTemplate> forChannel =
          templates.stream().filter(t -> t.getChannel().equals(channel.dbValue())).toList();
      if (forChannel.isEmpty()) {
        throw new IllegalArgumentException(
            "No active template '" + request.templateKey() + "' for channel " + channel.dbValue());
      }
      for (NotificationTemplate template : forChannel) {
        required.addAll(TemplateRenderer.placeholders(template.getSubject()));
        required.addAll(TemplateRenderer.placeholders(template.getBody()));
      }
    }
    Set<String> provided = request.data() == null ? Set.of() : request.data().keySet();
    Set<String> missing =
        required.stream()
            .filter(name -> !provided.contains(name))
            .collect(Collectors.toCollection(TreeSet::new));
    if (!missing.isEmpty()) {
      throw new IllegalArgumentException("Missing template data: " + String.join(", ", missing));
    }
  }
}
