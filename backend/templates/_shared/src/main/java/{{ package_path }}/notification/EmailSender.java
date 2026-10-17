package {{ base_package }}.notification;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.MailException;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Component;

/**
 * Sends one plain-text email over SMTP. "Not configured" (no {@link JavaMailSender} bean, because
 * {@code app.mail.host} is blank) is a normal outcome, not an error. Recipient addresses and
 * message bodies are never logged.
 */
@Component
@Slf4j
public class EmailSender implements ChannelSender {

  private final ObjectProvider<JavaMailSender> mailSender;
  private final String from;

  /**
   * Wires the sender.
   *
   * @param mailSender the SMTP sender, absent when email is not configured
   * @param from the From address; blank leaves it to the mail server's default
   */
  public EmailSender(
      ObjectProvider<JavaMailSender> mailSender, @Value("${app.mail.from:}") String from) {
    this.mailSender = mailSender;
    this.from = from;
  }

  /** {@inheritDoc} */
  @Override
  public NotificationChannel channel() {
    return NotificationChannel.EMAIL;
  }

  /** {@inheritDoc} */
  @Override
  public SendOutcome send(SendRequest request) {
    JavaMailSender sender = mailSender.getIfAvailable();
    if (sender == null) {
      log.debug("Email skipped: SMTP is not configured");
      return SendOutcome.notConfigured();
    }
    SimpleMailMessage message = new SimpleMailMessage();
    if (!from.isBlank()) {
      message.setFrom(from);
    }
    message.setTo(request.recipient().email());
    message.setSubject(request.title());
    message.setText(request.body());
    try {
      sender.send(message);
      return SendOutcome.sent(null);
    } catch (MailException e) {
      // The exception message can contain the address and part of the body, so log only its type.
      log.atWarn()
          .addKeyValue("event.name", "notification.email.failed")
          .addKeyValue("error.type", e.getClass().getSimpleName())
          .log("Email send failed");
      return SendOutcome.failed();
    }
  }
}
