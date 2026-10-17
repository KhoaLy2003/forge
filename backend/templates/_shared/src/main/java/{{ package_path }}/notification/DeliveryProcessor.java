package {{ base_package }}.notification;

import {{ base_package }}.notification.entity.NotificationTemplate;
import {{ base_package }}.notification.repository.NotificationPreferenceRepository;
import {{ base_package }}.notification.repository.NotificationTemplateRepository;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * Sends one claimed delivery. Deliberately not transactional: it performs network I/O (SMTP, other
 * providers) and must never hold a database connection while doing so. Every state change is a
 * single statement through {@link NotificationQueries}, and one failing delivery never stops the
 * batch.
 *
 * <p>Recipient addresses, message bodies and exception messages are never logged; failures are
 * logged with a stable event name and the exception type only.
 */
@Component
@Slf4j
public class DeliveryProcessor {

  /** Seconds to wait before the Nth retry, indexed by failed attempts so far minus one. */
  private static final int[] RETRY_DELAYS_SECONDS = {60, 300, 1800, 7200};

  private static final int MAX_ERROR_LENGTH = 500;

  private final NotificationQueries queries;
  private final NotificationTemplateRepository templateRepository;
  private final NotificationPreferenceRepository preferenceRepository;
  private final ObjectProvider<RecipientDirectory> recipientDirectory;
  private final Map<NotificationChannel, ChannelSender> senders =
      new EnumMap<>(NotificationChannel.class);
  private final int maxAttempts;
  private final String defaultLocale;

  /**
   * Wires the processor.
   *
   * @param queries the outbox SQL
   * @param templateRepository the message templates
   * @param preferenceRepository the recipients' channel switches
   * @param recipientDirectory the project's recipient lookup; optional, see {@link
   *     RecipientDirectory#NONE}
   * @param channelSenders every registered external channel sender
   * @param maxAttempts failed attempts after which a delivery is given up on
   * @param defaultLocale the locale used when the recipient's has no template
   */
  public DeliveryProcessor(
      NotificationQueries queries,
      NotificationTemplateRepository templateRepository,
      NotificationPreferenceRepository preferenceRepository,
      ObjectProvider<RecipientDirectory> recipientDirectory,
      List<ChannelSender> channelSenders,
      @Value("${app.notifications.max-attempts:5}") int maxAttempts,
      @Value("${app.notifications.default-locale:en}") String defaultLocale) {
    this.queries = queries;
    this.templateRepository = templateRepository;
    this.preferenceRepository = preferenceRepository;
    this.recipientDirectory = recipientDirectory;
    channelSenders.forEach(sender -> senders.put(sender.channel(), sender));
    this.maxAttempts = maxAttempts;
    this.defaultLocale = defaultLocale;
  }

  /**
   * Processes one claimed delivery to a terminal or retry state. Never throws.
   *
   * @param job the claimed delivery
   */
  public void process(NotificationQueries.DeliveryJob job) {
    try {
      doProcess(job);
    } catch (RuntimeException e) {
      // The message can hold the address or part of the body, so only the type is logged.
      log.atWarn()
          .addKeyValue("event.name", "notification.delivery.failed")
          .addKeyValue("delivery.id", job.id())
          .addKeyValue("error.type", e.getClass().getSimpleName())
          .log("Delivery failed");
      try {
        retryOrFail(job, e.getClass().getSimpleName() + ": " + e.getMessage());
      } catch (RuntimeException inner) {
        log.atError()
            .addKeyValue("event.name", "notification.delivery.record_failed")
            .addKeyValue("delivery.id", job.id())
            .addKeyValue("error.type", inner.getClass().getSimpleName())
            .log("Could not record the failure of a delivery");
      }
    }
  }

  private void doProcess(NotificationQueries.DeliveryJob job) {
    NotificationQueries.NotificationInfo info =
        queries
            .findNotification(job.notificationId())
            .orElseThrow(
                () -> new IllegalStateException("Notification missing: " + job.notificationId()));
    if (NotificationStatus.CANCELLED.equals(info.status())) {
      skip(job, DeliveryStatus.SKIP_CANCELLED);
      return;
    }
    NotificationChannel channel = NotificationChannel.fromDb(job.channel());
    if (channel == NotificationChannel.EMAIL && emailOptedOut(job)) {
      skip(job, DeliveryStatus.SKIP_OPTED_OUT);
      return;
    }

    Optional<Recipient> recipient = lookUp(job);
    if (channel != NotificationChannel.IN_APP && !hasAddress(recipient)) {
      skip(job, DeliveryStatus.SKIP_RECIPIENT_UNRESOLVED);
      return;
    }

    String locale =
        recipient.map(Recipient::locale).filter(l -> !l.isBlank()).orElse(defaultLocale);
    NotificationTemplate template = findTemplate(info.templateKey(), channel, locale).orElse(null);
    if (template == null) {
      skip(job, DeliveryStatus.SKIP_NO_TEMPLATE);
      return;
    }
    String title = TemplateRenderer.render(template.getSubject(), info.data());
    String body = TemplateRenderer.render(template.getBody(), info.data());

    if (channel == NotificationChannel.IN_APP) {
      queries.markInAppSent(job.id(), title, body);
      return;
    }
    send(job, channel, recipient.orElseThrow(), title, body);
  }

  private boolean emailOptedOut(NotificationQueries.DeliveryJob job) {
    return preferenceRepository
        .findByRecipientIdAndDeletedAtIsNull(job.recipientId())
        .map(preference -> !preference.isEmailEnabled())
        .orElse(false);
  }

  private Optional<Recipient> lookUp(NotificationQueries.DeliveryJob job) {
    return recipientDirectory.getIfAvailable(() -> RecipientDirectory.NONE).find(job.recipientId());
  }

  private static boolean hasAddress(Optional<Recipient> recipient) {
    return recipient.map(Recipient::email).filter(email -> !email.isBlank()).isPresent();
  }

  private Optional<NotificationTemplate> findTemplate(
      String templateKey, NotificationChannel channel, String locale) {
    return templateRepository
        .findByTemplateKeyAndChannelAndLocaleAndActiveTrueAndDeletedAtIsNull(
            templateKey, channel.dbValue(), locale)
        .or(
            () ->
                templateRepository
                    .findByTemplateKeyAndChannelAndLocaleAndActiveTrueAndDeletedAtIsNull(
                        templateKey, channel.dbValue(), defaultLocale));
  }

  private void send(
      NotificationQueries.DeliveryJob job,
      NotificationChannel channel,
      Recipient recipient,
      String title,
      String body) {
    ChannelSender sender = senders.get(channel);
    if (sender == null) {
      skip(job, notConfiguredReason(channel));
      return;
    }
    ChannelSender.SendOutcome outcome =
        sender.send(
            new ChannelSender.SendRequest(job.id(), job.recipientId(), recipient, title, body));
    switch (outcome.result()) {
      case SENT -> queries.markSent(job.id(), outcome.providerMessageId());
      case NOT_CONFIGURED -> skip(job, notConfiguredReason(channel));
      case FAILED -> retryOrFail(job, channel.dbValue() + " send failed");
    }
  }

  private static String notConfiguredReason(NotificationChannel channel) {
    return channel.dbValue() + "_not_configured";
  }

  private void skip(NotificationQueries.DeliveryJob job, String reason) {
    queries.markSkipped(job.id(), reason);
    // A missing template is a configuration bug worth attention; the other reasons are routine.
    var event = DeliveryStatus.SKIP_NO_TEMPLATE.equals(reason) ? log.atWarn() : log.atDebug();
    event
        .addKeyValue("event.name", "notification.delivery.skipped")
        .addKeyValue("delivery.id", job.id())
        .addKeyValue("skip.reason", reason)
        .log("Delivery skipped");
  }

  private void retryOrFail(NotificationQueries.DeliveryJob job, String error) {
    int attempts = job.attemptCount() + 1;
    String message =
        error.length() > MAX_ERROR_LENGTH ? error.substring(0, MAX_ERROR_LENGTH) : error;
    if (attempts >= maxAttempts) {
      queries.markFailed(job.id(), attempts, message);
    } else {
      int delay = RETRY_DELAYS_SECONDS[Math.min(attempts - 1, RETRY_DELAYS_SECONDS.length - 1)];
      queries.scheduleRetry(job.id(), attempts, delay, message);
    }
  }
}
