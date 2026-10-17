package {{ base_package }}.notification;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import {{ base_package }}.notification.entity.NotificationPreference;
import {{ base_package }}.notification.entity.NotificationTemplate;
import {{ base_package }}.notification.repository.NotificationPreferenceRepository;
import {{ base_package }}.notification.repository.NotificationTemplateRepository;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.function.Supplier;
import java.util.stream.Collectors;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.mockito.ArgumentCaptor;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;

{% raw %}class DeliveryProcessorTest {

  private final NotificationQueries queries = mock(NotificationQueries.class);
  private final NotificationTemplateRepository templates =
      mock(NotificationTemplateRepository.class);
  private final NotificationPreferenceRepository preferences =
      mock(NotificationPreferenceRepository.class);
  private final RecipientDirectory directory = mock(RecipientDirectory.class);
  private final ChannelSender emailSender = mock(ChannelSender.class);

  @SuppressWarnings("unchecked")
  private final ObjectProvider<RecipientDirectory> directoryProvider = mock(ObjectProvider.class);

  private final Logger logger = (Logger) LoggerFactory.getLogger(DeliveryProcessor.class);
  private final ListAppender<ILoggingEvent> logs = new ListAppender<>();

  private final UUID notificationId = UUID.randomUUID();
  private final UUID recipientId = UUID.randomUUID();
  private final UUID deliveryId = UUID.randomUUID();

  private DeliveryProcessor processor;

  @BeforeEach
  @SuppressWarnings("unchecked")
  void setUp() {
    when(emailSender.channel()).thenReturn(NotificationChannel.EMAIL);
    when(directoryProvider.getIfAvailable(any(Supplier.class))).thenReturn(directory);
    when(preferences.findByRecipientIdAndDeletedAtIsNull(recipientId)).thenReturn(Optional.empty());
    processor = processor(5, List.of(emailSender));
    logs.start();
    logger.addAppender(logs);
    logger.setLevel(Level.DEBUG);
  }

  @AfterEach
  void detachLogs() {
    logger.detachAppender(logs);
    logger.setLevel(null);
  }

  private DeliveryProcessor processor(int maxAttempts, List<ChannelSender> senders) {
    return new DeliveryProcessor(
        queries, templates, preferences, directoryProvider, senders, maxAttempts, "en");
  }

  private NotificationQueries.DeliveryJob job(String channel, int attemptCount) {
    return new NotificationQueries.DeliveryJob(
        deliveryId, notificationId, recipientId, channel, attemptCount);
  }

  private void givenNotification(String status) {
    when(queries.findNotification(notificationId))
        .thenReturn(
            Optional.of(
                new NotificationQueries.NotificationInfo(
                    notificationId, "WELCOME", "welcome", status, Map.of("name", "Mia"))));
  }

  private void givenTemplate(String channel, String locale, String subject, String body) {
    when(templates.findByTemplateKeyAndChannelAndLocaleAndActiveTrueAndDeletedAtIsNull(
            "welcome", channel, locale))
        .thenReturn(
            Optional.of(
                NotificationTemplate.builder()
                    .templateKey("welcome")
                    .channel(channel)
                    .locale(locale)
                    .subject(subject)
                    .body(body)
                    .build()));
  }

  private void givenRecipient(String email, String locale) {
    when(directory.find(recipientId)).thenReturn(Optional.of(new Recipient(email, locale)));
  }

  // ---------------------------------------------------------------- skipping

  @Test
  void aCancelledNotificationIsSkippedWithoutLookingAnythingElseUp() {
    givenNotification(NotificationStatus.CANCELLED);

    processor.process(job("email", 0));

    verify(queries).markSkipped(deliveryId, DeliveryStatus.SKIP_CANCELLED);
    verifyNoInteractions(templates, directory);
    verify(emailSender, never()).send(any());
  }

  @Test
  void emailIsSkippedWhenTheRecipientOptedOut() {
    givenNotification(NotificationStatus.QUEUED);
    NotificationPreference optedOut =
        NotificationPreference.builder().recipientId(recipientId).build();
    optedOut.setEmailEnabled(false);
    when(preferences.findByRecipientIdAndDeletedAtIsNull(recipientId))
        .thenReturn(Optional.of(optedOut));

    processor.process(job("email", 0));

    verify(queries).markSkipped(deliveryId, DeliveryStatus.SKIP_OPTED_OUT);
    verify(emailSender, never()).send(any());
    verifyNoInteractions(directory);
  }

  @Test
  void emailIsSkippedWithRecipientUnresolvedWhenTheDirectoryFindsNobody() {
    givenNotification(NotificationStatus.QUEUED);
    when(directory.find(recipientId)).thenReturn(Optional.empty());

    processor.process(job("email", 0));

    verify(queries).markSkipped(deliveryId, DeliveryStatus.SKIP_RECIPIENT_UNRESOLVED);
    verify(emailSender, never()).send(any());
    verify(queries, never()).scheduleRetry(any(), anyInt(), anyInt(), anyString());
  }

  @Test
  @SuppressWarnings("unchecked")
  void withNoDirectoryBeanAtAllEmailIsSkippedAsUnresolvedAndNothingFails() {
    when(directoryProvider.getIfAvailable(any(Supplier.class)))
        .thenAnswer(call -> ((Supplier<?>) call.getArgument(0)).get());
    givenNotification(NotificationStatus.QUEUED);

    processor.process(job("email", 0));

    verify(queries).markSkipped(deliveryId, DeliveryStatus.SKIP_RECIPIENT_UNRESOLVED);
    verify(queries, never()).scheduleRetry(any(), anyInt(), anyInt(), anyString());
  }

  @Test
  void emailIsSkippedAsUnresolvedWhenTheRecipientHasNoAddress() {
    givenNotification(NotificationStatus.QUEUED);
    givenRecipient("  ", "en");

    processor.process(job("email", 0));

    verify(queries).markSkipped(deliveryId, DeliveryStatus.SKIP_RECIPIENT_UNRESOLVED);
    verify(emailSender, never()).send(any());
  }

  @Test
  void aMissingTemplateIsSkippedAndLoggedAsAWarning() {
    givenNotification(NotificationStatus.QUEUED);
    givenRecipient("mia@example.org", "en");
    when(templates.findByTemplateKeyAndChannelAndLocaleAndActiveTrueAndDeletedAtIsNull(
            anyString(), anyString(), anyString()))
        .thenReturn(Optional.empty());

    processor.process(job("email", 0));

    verify(queries).markSkipped(deliveryId, DeliveryStatus.SKIP_NO_TEMPLATE);
    assertThat(logs.list).anySatisfy(event -> assertThat(event.getLevel()).isEqualTo(Level.WARN));
  }

  @Test
  void aRecipientsLocaleFallsBackToTheDefaultLocaleWhenItHasNoTemplate() {
    givenNotification(NotificationStatus.QUEUED);
    givenRecipient("mia@example.org", "vi");
    when(templates.findByTemplateKeyAndChannelAndLocaleAndActiveTrueAndDeletedAtIsNull(
            "welcome", "email", "vi"))
        .thenReturn(Optional.empty());
    givenTemplate("email", "en", "Hello {{name}}", "Body for {{name}}");
    when(emailSender.send(any())).thenReturn(ChannelSender.SendOutcome.sent("m-1"));

    processor.process(job("email", 0));

    ArgumentCaptor<ChannelSender.SendRequest> sent =
        ArgumentCaptor.forClass(ChannelSender.SendRequest.class);
    verify(emailSender).send(sent.capture());
    assertThat(sent.getValue().title()).isEqualTo("Hello Mia");
  }

  @Test
  void theRecipientsOwnLocaleIsPreferredWhenATemplateExistsForIt() {
    givenNotification(NotificationStatus.QUEUED);
    givenRecipient("mia@example.org", "vi");
    givenTemplate("email", "vi", "Xin chao {{name}}", "Noi dung");
    givenTemplate("email", "en", "Hello {{name}}", "Body");
    when(emailSender.send(any())).thenReturn(ChannelSender.SendOutcome.sent(null));

    processor.process(job("email", 0));

    ArgumentCaptor<ChannelSender.SendRequest> sent =
        ArgumentCaptor.forClass(ChannelSender.SendRequest.class);
    verify(emailSender).send(sent.capture());
    assertThat(sent.getValue().title()).isEqualTo("Xin chao Mia");
  }

  // ------------------------------------------------------------------ in-app

  @Test
  void inAppStoresTheRenderedTextAndIgnoresEmailPreferences() {
    givenNotification(NotificationStatus.QUEUED);
    NotificationPreference optedOut =
        NotificationPreference.builder().recipientId(recipientId).build();
    optedOut.setEmailEnabled(false);
    when(preferences.findByRecipientIdAndDeletedAtIsNull(recipientId))
        .thenReturn(Optional.of(optedOut));
    when(directory.find(recipientId)).thenReturn(Optional.empty());
    givenTemplate("in_app", "en", "Hi {{name}}", "Welcome {{ name }}!");

    processor.process(job("in_app", 0));

    verify(queries).markInAppSent(deliveryId, "Hi Mia", "Welcome Mia!");
    verify(emailSender, never()).send(any());
  }

  @Test
  void inAppUsesTheRecipientsLocaleWhenTheDirectoryKnowsIt() {
    givenNotification(NotificationStatus.QUEUED);
    givenRecipient("mia@example.org", "vi");
    givenTemplate("in_app", "vi", "Chao {{name}}", "Xin chao");

    processor.process(job("in_app", 0));

    verify(queries).markInAppSent(deliveryId, "Chao Mia", "Xin chao");
  }

  // ------------------------------------------------------------------- email

  @Test
  void emailIsSentWithTheRenderedTextAndRecordedAsSent() {
    givenNotification(NotificationStatus.QUEUED);
    givenRecipient("mia@example.org", "en");
    givenTemplate("email", "en", "Hi {{name}}", "Body {{name}}");
    when(emailSender.send(any())).thenReturn(ChannelSender.SendOutcome.sent("provider-9"));

    processor.process(job("email", 0));

    ArgumentCaptor<ChannelSender.SendRequest> sent =
        ArgumentCaptor.forClass(ChannelSender.SendRequest.class);
    verify(emailSender).send(sent.capture());
    assertThat(sent.getValue().deliveryId()).isEqualTo(deliveryId);
    assertThat(sent.getValue().recipientId()).isEqualTo(recipientId);
    assertThat(sent.getValue().recipient().email()).isEqualTo("mia@example.org");
    assertThat(sent.getValue().title()).isEqualTo("Hi Mia");
    assertThat(sent.getValue().body()).isEqualTo("Body Mia");
    verify(queries).markSent(deliveryId, "provider-9");
  }

  @Test
  void emailNotConfiguredIsSkippedNotRetried() {
    givenNotification(NotificationStatus.QUEUED);
    givenRecipient("mia@example.org", "en");
    givenTemplate("email", "en", "Hi", "Body");
    when(emailSender.send(any())).thenReturn(ChannelSender.SendOutcome.notConfigured());

    processor.process(job("email", 0));

    verify(queries).markSkipped(deliveryId, DeliveryStatus.SKIP_EMAIL_NOT_CONFIGURED);
    verify(queries, never()).scheduleRetry(any(), anyInt(), anyInt(), anyString());
  }

  @Test
  void aChannelWithoutAnyRegisteredSenderIsSkippedAsNotConfigured() {
    DeliveryProcessor withoutSenders = processor(5, List.of());
    givenNotification(NotificationStatus.QUEUED);
    givenRecipient("mia@example.org", "en");
    givenTemplate("email", "en", "Hi", "Body");

    withoutSenders.process(job("email", 0));

    verify(queries).markSkipped(deliveryId, "email_not_configured");
  }

  // ------------------------------------------------------------ retry / fail

  @ParameterizedTest
  @CsvSource({"0,1,60", "1,2,300", "2,3,1800", "3,4,7200"})
  void aFailedSendIsRetriedWithIncreasingBackoff(
      int attemptsSoFar, int attempts, int delaySeconds) {
    givenNotification(NotificationStatus.QUEUED);
    givenRecipient("mia@example.org", "en");
    givenTemplate("email", "en", "Hi", "Body");
    when(emailSender.send(any())).thenReturn(ChannelSender.SendOutcome.failed());

    processor.process(job("email", attemptsSoFar));

    verify(queries).scheduleRetry(eq(deliveryId), eq(attempts), eq(delaySeconds), anyString());
    verify(queries, never()).markFailed(any(), anyInt(), anyString());
  }

  @Test
  void theLastAllowedAttemptMarksTheDeliveryFailedInsteadOfRetrying() {
    givenNotification(NotificationStatus.QUEUED);
    givenRecipient("mia@example.org", "en");
    givenTemplate("email", "en", "Hi", "Body");
    when(emailSender.send(any())).thenReturn(ChannelSender.SendOutcome.failed());

    processor.process(job("email", 4));

    verify(queries).markFailed(eq(deliveryId), eq(5), anyString());
    verify(queries, never()).scheduleRetry(any(), anyInt(), anyInt(), anyString());
  }

  @Test
  void theBackoffStaysAtItsCapWhenMoreAttemptsAreAllowed() {
    DeliveryProcessor patient = processor(10, List.of(emailSender));
    givenNotification(NotificationStatus.QUEUED);
    givenRecipient("mia@example.org", "en");
    givenTemplate("email", "en", "Hi", "Body");
    when(emailSender.send(any())).thenReturn(ChannelSender.SendOutcome.failed());

    patient.process(job("email", 6));

    verify(queries).scheduleRetry(eq(deliveryId), eq(7), eq(7200), anyString());
  }

  @Test
  void anUnexpectedExceptionIsContainedRetriedAndLoggedWithoutPersonalData() {
    givenNotification(NotificationStatus.QUEUED);
    givenRecipient("mia@example.org", "en");
    givenTemplate("email", "en", "Hi {{name}}", "Body");
    when(emailSender.send(any()))
        .thenThrow(new IllegalStateException("boom for mia@example.org: Body"));

    processor.process(job("email", 0));

    verify(queries).scheduleRetry(eq(deliveryId), eq(1), eq(60), anyString());
    ILoggingEvent failure =
        logs.list.stream()
            .filter(e -> e.getKeyValuePairs() != null)
            .filter(
                e ->
                    e.getKeyValuePairs().stream()
                        .anyMatch(
                            kv ->
                                kv.key.equals("event.name")
                                    && kv.value.equals("notification.delivery.failed")))
            .findFirst()
            .orElseThrow();
    assertThat(failure.getLevel()).isEqualTo(Level.WARN);
    String everything =
        failure.getFormattedMessage()
            + failure.getKeyValuePairs().stream()
                .map(kv -> kv.key + "=" + kv.value)
                .collect(Collectors.joining(","));
    assertThat(everything)
        .contains("IllegalStateException")
        .doesNotContain("mia@example.org")
        .doesNotContain("Body");
    assertThat(failure.getThrowableProxy()).isNull();
  }

  @Test
  void aMissingNotificationRowIsRetriedRatherThanThrown() {
    when(queries.findNotification(notificationId)).thenReturn(Optional.empty());

    processor.process(job("email", 0));

    verify(queries).scheduleRetry(eq(deliveryId), eq(1), eq(60), anyString());
  }

  @Test
  void anUnknownChannelInTheDatabaseIsRetriedAndEventuallyFails() {
    givenNotification(NotificationStatus.QUEUED);

    processor.process(job("sms", 4));

    verify(queries).markFailed(eq(deliveryId), eq(5), anyString());
  }

  @Test
  void ifRecordingTheFailureAlsoFailsProcessStillDoesNotThrow() {
    givenNotification(NotificationStatus.QUEUED);
    givenRecipient("mia@example.org", "en");
    givenTemplate("email", "en", "Hi", "Body");
    when(emailSender.send(any())).thenReturn(ChannelSender.SendOutcome.failed());
    doThrow(new IllegalStateException("db gone"))
        .when(queries)
        .scheduleRetry(any(), anyInt(), anyInt(), anyString());

    processor.process(job("email", 0));

    assertThat(logs.list).anySatisfy(event -> assertThat(event.getLevel()).isEqualTo(Level.ERROR));
  }

  @Test
  void theStoredErrorTextIsTruncatedToTheColumnLimit() {
    givenNotification(NotificationStatus.QUEUED);
    givenRecipient("mia@example.org", "en");
    givenTemplate("email", "en", "Hi", "Body");
    when(emailSender.send(any())).thenThrow(new IllegalStateException("x".repeat(2000)));

    processor.process(job("email", 0));

    ArgumentCaptor<String> error = ArgumentCaptor.forClass(String.class);
    verify(queries).scheduleRetry(eq(deliveryId), eq(1), eq(60), error.capture());
    assertThat(error.getValue()).hasSizeLessThanOrEqualTo(500);
  }
}{% endraw %}
