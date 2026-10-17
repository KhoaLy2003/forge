package {{ base_package }}.notification;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import java.util.UUID;
import java.util.stream.Collectors;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.mail.MailSendException;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;

class EmailSenderTest {

  @SuppressWarnings("unchecked")
  private final ObjectProvider<JavaMailSender> provider = mock(ObjectProvider.class);

  private final JavaMailSender mailSender = mock(JavaMailSender.class);

  private final Logger logger = (Logger) LoggerFactory.getLogger(EmailSender.class);
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

  private static ChannelSender.SendRequest request(String email) {
    return new ChannelSender.SendRequest(
        UUID.randomUUID(),
        UUID.randomUUID(),
        new Recipient(email, "en"),
        "Welcome, Mia!",
        "Thanks for joining, Mia.");
  }

  @Test
  void channelIsEmail() {
    assertThat(new EmailSender(provider, "").channel()).isEqualTo(NotificationChannel.EMAIL);
  }

  @Test
  void send_withoutAMailSenderBean_isNotConfiguredNotAnError() {
    when(provider.getIfAvailable()).thenReturn(null);

    ChannelSender.SendOutcome outcome =
        new EmailSender(provider, "").send(request("mia@example.org"));

    assertThat(outcome.result()).isEqualTo(ChannelSender.Result.NOT_CONFIGURED);
    assertThat(outcome.providerMessageId()).isNull();
  }

  @Test
  void send_handsTheMessageToTheMailSender() {
    when(provider.getIfAvailable()).thenReturn(mailSender);

    ChannelSender.SendOutcome outcome =
        new EmailSender(provider, "noreply@example.org").send(request("mia@example.org"));

    assertThat(outcome.result()).isEqualTo(ChannelSender.Result.SENT);
    ArgumentCaptor<SimpleMailMessage> sent = ArgumentCaptor.forClass(SimpleMailMessage.class);
    verify(mailSender).send(sent.capture());
    assertThat(sent.getValue().getFrom()).isEqualTo("noreply@example.org");
    assertThat(sent.getValue().getTo()).containsExactly("mia@example.org");
    assertThat(sent.getValue().getSubject()).isEqualTo("Welcome, Mia!");
    assertThat(sent.getValue().getText()).isEqualTo("Thanks for joining, Mia.");
  }

  @Test
  void send_withABlankFromAddress_leavesFromUnsetSoTheServerDefaultApplies() {
    when(provider.getIfAvailable()).thenReturn(mailSender);

    new EmailSender(provider, "  ").send(request("mia@example.org"));

    ArgumentCaptor<SimpleMailMessage> sent = ArgumentCaptor.forClass(SimpleMailMessage.class);
    verify(mailSender).send(sent.capture());
    assertThat(sent.getValue().getFrom()).isNull();
  }

  @Test
  void send_whenTheMailServerFails_returnsFailedWithoutThrowing() {
    when(provider.getIfAvailable()).thenReturn(mailSender);
    doThrow(new MailSendException("smtp down for mia@example.org: Thanks for joining"))
        .when(mailSender)
        .send(any(SimpleMailMessage.class));

    ChannelSender.SendOutcome outcome =
        new EmailSender(provider, "").send(request("mia@example.org"));

    assertThat(outcome.result()).isEqualTo(ChannelSender.Result.FAILED);
    assertThat(outcome.providerMessageId()).isNull();
  }

  @Test
  void send_whenTheMailServerFails_logsTheErrorTypeButNeverTheAddressOrBody() {
    when(provider.getIfAvailable()).thenReturn(mailSender);
    doThrow(new MailSendException("smtp down for mia@example.org: Thanks for joining"))
        .when(mailSender)
        .send(any(SimpleMailMessage.class));

    new EmailSender(provider, "").send(request("mia@example.org"));

    assertThat(logs.list).hasSize(1);
    ILoggingEvent event = logs.list.get(0);
    String everything =
        event.getFormattedMessage()
            + event.getKeyValuePairs().stream()
                .map(kv -> kv.key + "=" + kv.value)
                .collect(Collectors.joining(","));
    assertThat(everything)
        .contains("notification.email.failed")
        .contains("MailSendException")
        .doesNotContain("mia@example.org")
        .doesNotContain("Thanks for joining");
    assertThat(event.getThrowableProxy()).isNull();
  }

  @Test
  void send_neverContactsTheMailSenderWhenNotConfigured() {
    when(provider.getIfAvailable()).thenReturn(null);

    new EmailSender(provider, "").send(request("mia@example.org"));

    verify(mailSender, never()).send(any(SimpleMailMessage.class));
  }
}
