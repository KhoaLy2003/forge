package {{ base_package }}.common.config;

import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.LoggerContext;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.AppenderBase;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.function.Consumer;
import org.slf4j.MDC;
import org.springframework.boot.env.YamlPropertySourceLoader;
import org.springframework.boot.logging.logback.StructuredLogEncoder;
import org.springframework.core.env.Environment;
import org.springframework.core.env.PropertySource;
import org.springframework.core.io.ClassPathResource;
import org.springframework.mock.env.MockEnvironment;

/**
 * Test helper that formats real log events with Spring Boot's ECS structured-logging encoder
 * without starting an application context or a database. Each event is encoded while it is logged,
 * so MDC values are captured exactly as they would be in production.
 */
final class StructuredLogTestSupport {

  /** Captures every event logged through the logger as one encoded JSON line. */
  static final class Capture implements AutoCloseable {

    private final LoggerContext context = new LoggerContext();
    private final Logger logger = context.getLogger("structured.test");
    private final List<String> lines = new ArrayList<>();
    private RuntimeException failure;

    /** Captures with explicit properties on top of a minimal ECS setup. */
    Capture(Map<String, String> properties) {
      this(
          environment -> {
            environment.setProperty("logging.structured.format.console", "ecs");
            environment.setProperty("logging.structured.ecs.service.name", "demo-service");
            properties.forEach(environment::setProperty);
          });
    }

    /** Captures using the application's real {@code prod} configuration files. */
    static Capture withProdConfig() {
      return new Capture(
          environment -> {
            environment.getPropertySources().addLast(yaml("application-prod.yml"));
            environment.getPropertySources().addLast(yaml("application.yml"));
          });
    }

    private Capture(Consumer<MockEnvironment> configure) {
      // Use the adapter that MDC.put(...) writes to, so test MDC values reach the encoder.
      context.setMDCAdapter(MDC.getMDCAdapter());
      MockEnvironment environment = new MockEnvironment();
      configure.accept(environment);
      context.putObject(Environment.class.getName(), environment);

      StructuredLogEncoder encoder = new StructuredLogEncoder();
      encoder.setContext(context);
      encoder.setFormat("ecs");
      encoder.setCharset(StandardCharsets.UTF_8);
      encoder.start();

      AppenderBase<ILoggingEvent> appender =
          new AppenderBase<>() {
            @Override
            protected void append(ILoggingEvent event) {
              try {
                lines.add(new String(encoder.encode(event), StandardCharsets.UTF_8));
              } catch (RuntimeException e) {
                // AppenderBase would swallow this; surface it from log() so tests fail loudly.
                failure = e;
              }
            }
          };
      appender.setContext(context);
      appender.start();
      logger.addAppender(appender);
      logger.setLevel(Level.DEBUG);
      logger.setAdditive(false);
    }

    /** Runs the logging statements and returns every encoded line produced. */
    List<String> log(Consumer<Logger> action) {
      action.accept(logger);
      if (failure != null) {
        throw new IllegalStateException("Encoding a log event failed", failure);
      }
      return List.copyOf(lines);
    }

    @Override
    public void close() {
      context.stop();
    }
  }

  private static PropertySource<?> yaml(String classpathFile) {
    try {
      return new YamlPropertySourceLoader()
          .load(classpathFile, new ClassPathResource(classpathFile))
          .get(0);
    } catch (IOException e) {
      throw new IllegalStateException("Cannot load " + classpathFile, e);
    }
  }

  private StructuredLogTestSupport() {}
}
