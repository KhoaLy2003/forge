package {{ base_package }};

import java.util.TimeZone;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Application entry point.
 *
 * <p>Beyond bootstrapping the Spring context, this class pins the JVM's default timezone to UTC in
 * a static initializer that runs before any Spring bean (including Liquibase's datasource) is
 * created. This matters because Liquibase opens a JDBC connection during context startup, before
 * Hibernate/Spring have a chance to configure a session timezone, so the JVM default is what PGJDBC
 * negotiates with Postgres on that first connection.
 */
@SpringBootApplication
public class {{ app_class_name }}Application {

  static {
    // Pin the JVM default timezone before any JDBC connection (including Liquibase's,
    // which runs before Hibernate is configured) negotiates a session timezone with
    // Postgres. Without this, PGJDBC sends the host OS's IANA zone id verbatim, which
    // fails with "invalid value for parameter TimeZone" on any host whose zone isn't in
    // the postgres image's minimal tzdata subset (e.g. "Asia/Saigon").
    TimeZone.setDefault(TimeZone.getTimeZone("UTC"));
  }

  /**
   * Boots the Spring application context.
   *
   * @param args command-line arguments forwarded to {@link SpringApplication#run}
   */
  public static void main(String[] args) {
    SpringApplication.run({{ app_class_name }}Application.class, args);
  }
}
