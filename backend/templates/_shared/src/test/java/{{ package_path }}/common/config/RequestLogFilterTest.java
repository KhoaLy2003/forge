package {{ base_package }}.common.config;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import java.util.Map;
import java.util.stream.Collectors;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.http.HttpStatus;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

class RequestLogFilterTest {

  private static final String SENSITIVE_BODY =
      "{\"email\":\"person@example.org\",\"pin\":\"4821\"}";

  @RestController
  static class Probe {
    @GetMapping("/api/v1/things/{id}")
    String byId(@PathVariable String id) {
      return "ok";
    }

    @PostMapping("/api/v1/things")
    String create(@RequestBody String body) {
      return "ok";
    }

    @GetMapping("/actuator/health")
    String health() {
      return "UP";
    }

    @GetMapping("/probe/server-error")
    @ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
    String serverError() {
      return "boom";
    }

    @GetMapping("/probe/throws")
    String throwsUp() {
      throw new IllegalStateException("escapes the filter chain");
    }
  }

  private final Logger logger = (Logger) LoggerFactory.getLogger(RequestLogFilter.class);
  private final ListAppender<ILoggingEvent> logs = new ListAppender<>();

  @BeforeEach
  void attach() {
    logger.setLevel(Level.DEBUG);
    logs.start();
    logger.addAppender(logs);
  }

  @AfterEach
  void detach() {
    logger.detachAppender(logs);
    logger.setLevel(null);
    MDC.clear();
  }

  private static MockMvc mvc(long slowMs) {
    return MockMvcBuilders.standaloneSetup(new Probe())
        .addFilters(new CorrelationIdFilter(), new RequestLogFilter(slowMs))
        .build();
  }

  private static Map<String, Object> fields(ILoggingEvent event) {
    return event.getKeyValuePairs().stream()
        .collect(Collectors.toMap(kv -> kv.key, kv -> kv.value));
  }

  @Test
  void logsMethodRouteTemplateStatusAndDuration_withRequestId() throws Exception {
    mvc(60_000).perform(get("/api/v1/things/4c1d2f8e-1111-2222-3333-444455556666"));

    assertThat(logs.list).hasSize(1);
    ILoggingEvent event = logs.list.get(0);
    assertThat(event.getLevel()).isEqualTo(Level.INFO);
    assertThat(fields(event))
        .containsEntry("event.name", "http.request.completed")
        .containsEntry("http.request.method", "GET")
        .containsEntry("http.route", "/api/v1/things/{id}")
        .containsEntry("http.response.status_code", 200)
        .containsKey("duration_ms");
    assertThat(event.getMDCPropertyMap()).containsKey(CorrelationIdFilter.MDC_KEY);
    assertThat(event.getFormattedMessage()).doesNotContain("4c1d2f8e");
  }

  @Test
  void neverLogsQueryStringBodyOrCredentials() throws Exception {
    mvc(60_000)
        .perform(
            post("/api/v1/things")
                .queryParam("email", "query-person@example.org")
                .queryParam("token", "QUERY-SECRET")
                .header("Authorization", "Bearer SECRET-TOKEN-VALUE")
                .cookie(new jakarta.servlet.http.Cookie("session", "SECRET-COOKIE-VALUE"))
                .contentType("application/json")
                .content(SENSITIVE_BODY));

    assertThat(logs.list).hasSize(1);
    ILoggingEvent event = logs.list.get(0);
    String everything =
        event.getFormattedMessage() + fields(event) + event.getMDCPropertyMap().toString();
    assertThat(everything)
        .doesNotContain("query-person@example.org")
        .doesNotContain("QUERY-SECRET")
        .doesNotContain("person@example.org")
        .doesNotContain("4821")
        .doesNotContain("SECRET-TOKEN-VALUE")
        .doesNotContain("SECRET-COOKIE-VALUE");
  }

  @Test
  void unmatchedRequestWithSecretQuery_reportsPlaceholderRouteNotTheRawPathOrQuery()
      throws Exception {
    mvc(60_000)
        .perform(
            get("/no/such/9a8b7c6d-0000-1111-2222-333344445555")
                .queryParam("token", "secret")
                .queryParam("email", "a@b.c"));

    assertThat(logs.list).hasSize(1);
    ILoggingEvent event = logs.list.get(0);
    assertThat(fields(event))
        .containsEntry("http.route", "UNMATCHED")
        .containsEntry("http.response.status_code", 404);
    String everything = event.getFormattedMessage() + fields(event);
    assertThat(everything)
        .doesNotContain("9a8b7c6d")
        .doesNotContain("secret")
        .doesNotContain("a@b.c");
  }

  @Test
  void serverError_isLoggedAtError() throws Exception {
    mvc(60_000).perform(get("/probe/server-error"));

    assertThat(logs.list).hasSize(1);
    assertThat(logs.list.get(0).getLevel()).isEqualTo(Level.ERROR);
    assertThat(fields(logs.list.get(0))).containsEntry("http.response.status_code", 500);
  }

  @Test
  void exceptionEscapingTheChain_isLoggedOnceAs500AtErrorAndStillPropagates() {
    MDC.put("kept", "yes");

    assertThatThrownBy(() -> mvc(60_000).perform(get("/probe/throws")))
        .hasRootCauseInstanceOf(IllegalStateException.class);

    assertThat(logs.list).hasSize(1);
    assertThat(logs.list.get(0).getLevel()).isEqualTo(Level.ERROR);
    assertThat(fields(logs.list.get(0))).containsEntry("http.response.status_code", 500);
    assertThat(MDC.get(CorrelationIdFilter.MDC_KEY)).isNull();
    assertThat(MDC.get("kept")).isEqualTo("yes");
  }

  @Test
  void slowRequest_isLoggedAtWarn() throws Exception {
    mvc(0).perform(get("/api/v1/things/abc"));

    assertThat(logs.list).hasSize(1);
    assertThat(logs.list.get(0).getLevel()).isEqualTo(Level.WARN);
  }

  @Test
  void healthProbe_isLoggedAtDebugOnly() throws Exception {
    mvc(60_000).perform(get("/actuator/health"));

    assertThat(logs.list).hasSize(1);
    assertThat(logs.list.get(0).getLevel()).isEqualTo(Level.DEBUG);
  }

  @Test
  void healthProbe_isNotLoggedWhenDebugIsDisabled() throws Exception {
    logger.setLevel(Level.INFO);

    mvc(60_000).perform(get("/actuator/health"));

    assertThat(logs.list).isEmpty();
  }
}
