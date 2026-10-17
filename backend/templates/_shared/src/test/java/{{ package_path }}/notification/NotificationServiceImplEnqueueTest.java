package {{ base_package }}.notification;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyCollection;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import {{ base_package }}.notification.entity.NotificationTemplate;
import {{ base_package }}.notification.repository.NotificationPreferenceRepository;
import {{ base_package }}.notification.repository.NotificationTemplateRepository;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.slf4j.LoggerFactory;

{% raw %}class NotificationServiceImplEnqueueTest {

  private final NotificationQueries queries = mock(NotificationQueries.class);
  private final NotificationTemplateRepository templates =
      mock(NotificationTemplateRepository.class);
  private final NotificationPreferenceRepository preferences =
      mock(NotificationPreferenceRepository.class);
  private final NotificationServiceImpl service =
      new NotificationServiceImpl(queries, templates, preferences);

  private final Logger logger = (Logger) LoggerFactory.getLogger(NotificationServiceImpl.class);
  private final ListAppender<ILoggingEvent> logs = new ListAppender<>();

  @BeforeEach
  void attachLogs() {
    logs.start();
    logger.addAppender(logs);
  }

  @AfterEach
  void detachLogs() {
    logger.detachAppender(logs);
  }

  private static NotificationTemplate template(
      String key, String channel, String locale, String subject, String body) {
    return NotificationTemplate.builder()
        .templateKey(key)
        .channel(channel)
        .locale(locale)
        .subject(subject)
        .body(body)
        .build();
  }

  private void givenWelcomeTemplates() {
    when(templates.findByTemplateKeyAndActiveTrueAndDeletedAtIsNull("welcome"))
        .thenReturn(
            List.of(
                template("welcome", "in_app", "en", "Hi {{name}}", "Welcome {{name}}"),
                template("welcome", "email", "en", "Hi {{name}}", "Welcome {{name}}")));
  }

  private static NotificationRequest request(
      Set<NotificationChannel> channels,
      Set<UUID> recipients,
      Map<String, String> data,
      Instant scheduledAt,
      String idempotencyKey) {
    return new NotificationRequest(
        "WELCOME",
        "welcome",
        channels,
        Audience.users(recipients),
        data,
        scheduledAt,
        idempotencyKey,
        null);
  }

  private static NotificationRequest simple() {
    return request(
        Set.of(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        Set.of(UUID.randomUUID()),
        Map.of("name", "Mia"),
        null,
        null);
  }

  private void givenInsertSucceeds(UUID id) {
    when(queries.insertNotification(any(), any(), any(), any(), any(), any(), any(), any(), any()))
        .thenReturn(
            Optional.of(
                new NotificationQueries.Inserted(id, Instant.parse("2026-01-01T00:00:00Z"))));
  }

  // -------------------------------------------------------------- validation

  @Test
  void enqueue_withNoChannels_isRejectedBeforeAnythingIsWritten() {
    NotificationRequest request =
        request(Set.of(), Set.of(UUID.randomUUID()), Map.of(), null, null);

    assertThatThrownBy(() -> service.enqueue(request))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("channel");
    verifyNoInteractions(queries);
  }

  @Test
  void enqueue_withNullChannels_isRejected() {
    NotificationRequest request =
        new NotificationRequest(
            "T",
            "welcome",
            null,
            Audience.users(Set.of(UUID.randomUUID())),
            Map.of(),
            null,
            null,
            null);

    assertThatThrownBy(() -> service.enqueue(request)).isInstanceOf(IllegalArgumentException.class);
  }

  @Test
  void enqueue_withNoRecipients_isRejected() {
    NotificationRequest request =
        request(Set.of(NotificationChannel.IN_APP), Set.of(), Map.of(), null, null);

    assertThatThrownBy(() -> service.enqueue(request))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("1 and 500");
    verifyNoInteractions(queries);
  }

  @Test
  void enqueue_withMoreThanTheMaximumRecipients_isRejected() {
    Set<UUID> tooMany = new HashSet<>();
    for (int i = 0; i <= NotificationServiceImpl.MAX_EXPLICIT_RECIPIENTS; i++) {
      tooMany.add(UUID.randomUUID());
    }
    NotificationRequest request =
        request(Set.of(NotificationChannel.IN_APP), tooMany, Map.of(), null, null);

    assertThatThrownBy(() -> service.enqueue(request))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("500");
    verifyNoInteractions(queries);
  }

  @Test
  void enqueue_withExactlyTheMaximumRecipients_isAccepted() {
    givenWelcomeTemplates();
    givenInsertSucceeds(UUID.randomUUID());
    Set<UUID> max = new HashSet<>();
    for (int i = 0; i < NotificationServiceImpl.MAX_EXPLICIT_RECIPIENTS; i++) {
      max.add(UUID.randomUUID());
    }

    NotificationAck ack =
        service.enqueue(
            request(Set.of(NotificationChannel.IN_APP), max, Map.of("name", "x"), null, null));

    assertThat(ack.duplicate()).isFalse();
  }

  @Test
  void enqueue_withNoAudience_isRejected() {
    NotificationRequest request =
        new NotificationRequest(
            "T", "welcome", Set.of(NotificationChannel.IN_APP), null, Map.of(), null, null, null);

    assertThatThrownBy(() -> service.enqueue(request))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("audience");
  }

  @Test
  void enqueue_whenAChannelHasNoActiveTemplate_isRejectedNamingKeyAndChannel() {
    when(templates.findByTemplateKeyAndActiveTrueAndDeletedAtIsNull("welcome"))
        .thenReturn(List.of(template("welcome", "in_app", "en", "Hi", "Body")));

    assertThatThrownBy(() -> service.enqueue(simple()))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("welcome")
        .hasMessageContaining("email");
    verify(queries, never())
        .insertNotification(any(), any(), any(), any(), any(), any(), any(), any(), any());
  }

  @Test
  void enqueue_withAnUnknownTemplateKey_isRejected() {
    when(templates.findByTemplateKeyAndActiveTrueAndDeletedAtIsNull("welcome"))
        .thenReturn(List.of());

    assertThatThrownBy(() -> service.enqueue(simple()))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("No active template");
  }

  @Test
  void enqueue_withMissingTemplateData_isRejectedListingTheSortedNamesAndWritesNothing() {
    when(templates.findByTemplateKeyAndActiveTrueAndDeletedAtIsNull("welcome"))
        .thenReturn(
            List.of(
                template("welcome", "in_app", "en", "Hi {{name}}", "From {{team}} about {{topic}}"),
                template("welcome", "email", "en", "Hi", "Body")));
    NotificationRequest request =
        request(
            Set.of(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
            Set.of(UUID.randomUUID()),
            Map.of("name", "Mia"),
            null,
            null);

    assertThatThrownBy(() -> service.enqueue(request))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessage("Missing template data: team, topic");
    verify(queries, never())
        .insertNotification(any(), any(), any(), any(), any(), any(), any(), any(), any());
    verify(queries, never()).insertDeliveries(any(), anyCollection(), anyCollection(), any());
  }

  @Test
  void enqueue_withNullData_isRejectedWhenTheTemplateNeedsValues() {
    givenWelcomeTemplates();
    NotificationRequest request =
        request(Set.of(NotificationChannel.IN_APP), Set.of(UUID.randomUUID()), null, null, null);

    assertThatThrownBy(() -> service.enqueue(request))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("name");
  }

  @Test
  void enqueue_onlyChecksTemplatesOfTheRequestedChannels() {
    when(templates.findByTemplateKeyAndActiveTrueAndDeletedAtIsNull("welcome"))
        .thenReturn(
            List.of(
                template("welcome", "in_app", "en", "Hi", "Body"),
                template("welcome", "email", "en", "Hi {{onlyForEmail}}", "Body")));
    givenInsertSucceeds(UUID.randomUUID());

    NotificationAck ack =
        service.enqueue(
            request(
                Set.of(NotificationChannel.IN_APP),
                Set.of(UUID.randomUUID()),
                Map.of(),
                null,
                null));

    assertThat(ack).isNotNull();
  }

  // ---------------------------------------------------------------- happy path

  @Test
  void enqueue_dueNow_isQueuedWithDeliveriesForEveryRecipientAndChannel() {
    givenWelcomeTemplates();
    UUID notificationId = UUID.randomUUID();
    givenInsertSucceeds(notificationId);
    UUID first = UUID.randomUUID();
    UUID second = UUID.randomUUID();
    NotificationRequest request =
        request(
            Set.of(NotificationChannel.EMAIL, NotificationChannel.IN_APP),
            Set.of(first, second),
            Map.of("name", "Mia"),
            null,
            "key-1");

    NotificationAck ack = service.enqueue(request);

    assertThat(ack.id()).isEqualTo(notificationId);
    assertThat(ack.status()).isEqualTo(NotificationStatus.QUEUED);
    assertThat(ack.duplicate()).isFalse();
    assertThat(ack.createdAt()).isEqualTo(Instant.parse("2026-01-01T00:00:00Z"));
    verify(queries)
        .insertNotification(
            eq("WELCOME"),
            eq("welcome"),
            eq("in_app,email"),
            eq("users"),
            eq(Map.of("name", "Mia")),
            eq(NotificationStatus.QUEUED),
            eq(null),
            eq("key-1"),
            eq(null));
    @SuppressWarnings("unchecked")
    ArgumentCaptor<java.util.Collection<UUID>> recipients =
        ArgumentCaptor.forClass(java.util.Collection.class);
    verify(queries)
        .insertDeliveries(
            eq(notificationId), recipients.capture(), eq(List.of("in_app", "email")), eq(null));
    assertThat(recipients.getValue()).containsExactlyInAnyOrder(first, second);
  }

  @Test
  void enqueue_scheduledInTheFuture_isAcceptedAndDeliveriesCarryTheScheduleTime() {
    givenWelcomeTemplates();
    UUID notificationId = UUID.randomUUID();
    givenInsertSucceeds(notificationId);
    Instant later = Instant.now().plus(2, ChronoUnit.HOURS);

    NotificationAck ack =
        service.enqueue(
            request(
                Set.of(NotificationChannel.IN_APP),
                Set.of(UUID.randomUUID()),
                Map.of("name", "Mia"),
                later,
                null));

    assertThat(ack.status()).isEqualTo(NotificationStatus.ACCEPTED);
    verify(queries)
        .insertDeliveries(eq(notificationId), anyCollection(), eq(List.of("in_app")), eq(later));
  }

  @Test
  void enqueue_scheduledInThePast_isTreatedAsDueNow() {
    givenWelcomeTemplates();
    givenInsertSucceeds(UUID.randomUUID());

    NotificationAck ack =
        service.enqueue(
            request(
                Set.of(NotificationChannel.IN_APP),
                Set.of(UUID.randomUUID()),
                Map.of("name", "Mia"),
                Instant.now().minus(1, ChronoUnit.HOURS),
                null));

    assertThat(ack.status()).isEqualTo(NotificationStatus.QUEUED);
  }

  @Test
  void enqueue_withExtraDataKeysBeyondThePlaceholders_keepsThemAsContext() {
    givenWelcomeTemplates();
    givenInsertSucceeds(UUID.randomUUID());
    Map<String, String> data = Map.of("name", "Mia", "orderId", "o-1");

    service.enqueue(
        request(Set.of(NotificationChannel.IN_APP), Set.of(UUID.randomUUID()), data, null, null));

    verify(queries)
        .insertNotification(any(), any(), any(), any(), eq(data), any(), any(), any(), any());
  }

  // --------------------------------------------------------------- idempotency

  @Test
  void enqueue_withAnExistingIdempotencyKey_returnsTheOriginalAckAndWritesNoDeliveries() {
    givenWelcomeTemplates();
    when(queries.insertNotification(any(), any(), any(), any(), any(), any(), any(), any(), any()))
        .thenReturn(Optional.empty());
    UUID originalId = UUID.randomUUID();
    Instant created = Instant.parse("2025-05-05T00:00:00Z");
    when(queries.findByIdempotencyKey("key-1"))
        .thenReturn(
            Optional.of(new NotificationQueries.Existing(originalId, "completed", created)));

    NotificationAck ack =
        service.enqueue(
            request(
                Set.of(NotificationChannel.IN_APP),
                Set.of(UUID.randomUUID()),
                Map.of("name", "Mia"),
                null,
                "key-1"));

    assertThat(ack.duplicate()).isTrue();
    assertThat(ack.id()).isEqualTo(originalId);
    assertThat(ack.status()).isEqualTo("completed");
    assertThat(ack.createdAt()).isEqualTo(created);
    verify(queries, never()).insertDeliveries(any(), anyCollection(), anyCollection(), any());
  }

  @Test
  void enqueue_whenTheKeyConflictedButTheOriginalCannotBeFound_failsLoudly() {
    givenWelcomeTemplates();
    when(queries.insertNotification(any(), any(), any(), any(), any(), any(), any(), any(), any()))
        .thenReturn(Optional.empty());
    when(queries.findByIdempotencyKey("key-1")).thenReturn(Optional.empty());

    assertThatThrownBy(
            () ->
                service.enqueue(
                    request(
                        Set.of(NotificationChannel.IN_APP),
                        Set.of(UUID.randomUUID()),
                        Map.of("name", "Mia"),
                        null,
                        "key-1")))
        .isInstanceOf(IllegalStateException.class);
  }

  // ------------------------------------------------------------------- logging

  @Test
  void enqueue_logsAnAcceptedEventWithoutTemplateDataOrRecipients() {
    givenWelcomeTemplates();
    UUID notificationId = UUID.randomUUID();
    givenInsertSucceeds(notificationId);
    UUID recipient = UUID.randomUUID();

    service.enqueue(
        request(
            Set.of(NotificationChannel.IN_APP),
            Set.of(recipient),
            Map.of("name", "Mia-SECRET-NAME"),
            null,
            null));

    assertThat(logs.list).hasSize(1);
    ILoggingEvent event = logs.list.get(0);
    assertThat(event.getLevel()).isEqualTo(Level.INFO);
    Map<String, Object> fields =
        event.getKeyValuePairs().stream().collect(Collectors.toMap(kv -> kv.key, kv -> kv.value));
    assertThat(fields)
        .containsEntry("event.name", "notification.accepted")
        .containsEntry("notification.type", "WELCOME")
        .containsEntry("notification.status", "queued");
    String everything = event.getFormattedMessage() + fields;
    assertThat(everything).doesNotContain("Mia-SECRET-NAME").doesNotContain(recipient.toString());
  }
}{% endraw %}
