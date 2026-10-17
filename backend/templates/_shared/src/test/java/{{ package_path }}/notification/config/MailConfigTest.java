package {{ base_package }}.notification.config;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Properties;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.JavaMailSenderImpl;

class MailConfigTest {

  private final ApplicationContextRunner runner =
      new ApplicationContextRunner().withUserConfiguration(MailConfig.class);

  @Test
  void withNoHost_noMailSenderBeanExists() {
    runner.run(context -> assertThat(context).doesNotHaveBean(JavaMailSender.class));
  }

  @Test
  void withABlankHost_noMailSenderBeanExists() {
    runner
        .withPropertyValues("app.mail.host=")
        .run(context -> assertThat(context).doesNotHaveBean(JavaMailSender.class));
  }

  @Test
  void withAHost_aMailSenderIsConfiguredFromTheAppMailProperties() {
    runner
        .withPropertyValues(
            "app.mail.host=smtp.example.org",
            "app.mail.port=2525",
            "app.mail.username=user",
            "app.mail.password=secret",
            "app.mail.starttls=true")
        .run(
            context -> {
              assertThat(context).hasSingleBean(JavaMailSender.class);
              JavaMailSenderImpl sender =
                  (JavaMailSenderImpl) context.getBean(JavaMailSender.class);
              assertThat(sender.getHost()).isEqualTo("smtp.example.org");
              assertThat(sender.getPort()).isEqualTo(2525);
              assertThat(sender.getUsername()).isEqualTo("user");
              assertThat(sender.getPassword()).isEqualTo("secret");
              Properties properties = sender.getJavaMailProperties();
              assertThat(properties.getProperty("mail.smtp.auth")).isEqualTo("true");
              assertThat(properties.getProperty("mail.smtp.starttls.enable")).isEqualTo("true");
            });
  }

  @Test
  void withoutCredentials_smtpAuthIsNotRequested() {
    runner
        .withPropertyValues(
            "app.mail.host=localhost", "app.mail.port=25", "app.mail.starttls=false")
        .run(
            context -> {
              JavaMailSenderImpl sender =
                  (JavaMailSenderImpl) context.getBean(JavaMailSender.class);
              Properties properties = sender.getJavaMailProperties();
              assertThat(properties.getProperty("mail.smtp.auth")).isEqualTo("false");
              assertThat(properties.getProperty("mail.smtp.starttls.enable")).isEqualTo("false");
            });
  }

  @Test
  void theDefaultPortIs587() {
    runner
        .withPropertyValues("app.mail.host=smtp.example.org")
        .run(
            context ->
                assertThat(((JavaMailSenderImpl) context.getBean(JavaMailSender.class)).getPort())
                    .isEqualTo(587));
  }
}
