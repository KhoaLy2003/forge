package {{ base_package }}.notification.config;

import java.util.Properties;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnExpression;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.JavaMailSenderImpl;

/**
 * Creates the {@link JavaMailSender} for the email channel from the {@code app.mail.*} properties,
 * but only when {@code app.mail.host} is set. Without a host no bean exists, which the email sender
 * treats as "not configured" - so a fresh project starts and runs without any mail server.
 */
@Configuration
public class MailConfig {

  /**
   * Builds the SMTP sender.
   *
   * @param host the SMTP host
   * @param port the SMTP port
   * @param username the SMTP user; blank disables SMTP authentication
   * @param password the SMTP password
   * @param startTls whether to upgrade the connection with STARTTLS
   * @return a configured sender
   */
  @Bean
  @ConditionalOnExpression("!'${app.mail.host:}'.isBlank()")
  public JavaMailSender javaMailSender(
      @Value("${app.mail.host}") String host,
      @Value("${app.mail.port:587}") int port,
      @Value("${app.mail.username:}") String username,
      @Value("${app.mail.password:}") String password,
      @Value("${app.mail.starttls:true}") boolean startTls) {
    JavaMailSenderImpl sender = new JavaMailSenderImpl();
    sender.setHost(host);
    sender.setPort(port);
    boolean authenticate = !username.isBlank();
    if (authenticate) {
      sender.setUsername(username);
      sender.setPassword(password);
    }
    Properties properties = sender.getJavaMailProperties();
    properties.setProperty("mail.smtp.auth", String.valueOf(authenticate));
    properties.setProperty("mail.smtp.starttls.enable", String.valueOf(startTls));
    return sender;
  }
}
