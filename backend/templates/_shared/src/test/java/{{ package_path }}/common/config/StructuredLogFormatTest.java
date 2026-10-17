package {{ base_package }}.common.config;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

/**
 * Verifies the {@code prod} log format against the observability standard using the application's
 * real {@code application-prod.yml}: parseable JSON, required fields, injection resistance, bounded
 * stack traces and masking of sensitive values.
 */
class StructuredLogFormatTest {

  private static final JsonMapper JSON = JsonMapper.builder().build();

  @AfterEach
  void cleanMdc() {
    MDC.clear();
  }

  /** Reads a field that ECS may serialize either flat ("a.b") or nested ({"a":{"b":..}}). */
  private static JsonNode field(JsonNode root, String dotted) {
    if (root.has(dotted)) {
      return root.get(dotted);
    }
    JsonNode current = root;
    for (String part : dotted.split("\\.")) {
      current = current == null ? null : current.get(part);
    }
    return current;
  }

  private static JsonNode single(List<String> lines) {
    assertThat(lines).hasSize(1);
    return JSON.readTree(lines.get(0));
  }

  @Test
  void prodEventIsOneParseableJsonLineWithTheRequiredFields() {
    MDC.put(CorrelationIdFilter.MDC_KEY, "req-123");

    List<String> lines;
    try (var capture = StructuredLogTestSupport.Capture.withProdConfig()) {
      lines =
          capture.log(
              logger -> logger.atInfo().addKeyValue("event.name", "demo.event").log("hello"));
    }

    assertThat(lines.get(0).stripTrailing()).doesNotContain("\n");
    JsonNode event = single(lines);
    assertThat(field(event, "@timestamp").asString()).endsWith("Z");
    assertThat(field(event, "log.level").asString()).isEqualTo("INFO");
    assertThat(field(event, "message").asString()).isEqualTo("hello");
    assertThat(field(event, "service.name").asString()).isEqualTo("demo-service");
    assertThat(field(event, "service.version").asString()).isNotBlank().doesNotContain("@");
    assertThat(field(event, "service.environment").asString()).isEqualTo("production");
    assertThat(field(event, "request_id").asString()).isEqualTo("req-123");
    assertThat(field(event, "event.name").asString()).isEqualTo("demo.event");
  }

  @Test
  void injectedNewlinesAndJsonInUserValuesStayInsideOneLine() {
    String hostile = "x\n{\"fake\":true,\"log.level\":\"FATAL\"}";
    MDC.put(CorrelationIdFilter.MDC_KEY, hostile);

    List<String> lines;
    try (var capture = StructuredLogTestSupport.Capture.withProdConfig()) {
      lines = capture.log(logger -> logger.info("user said: {}", hostile));
    }

    assertThat(lines).hasSize(1);
    assertThat(lines.get(0).stripTrailing()).doesNotContain("\n");
    JsonNode event = single(lines);
    assertThat(event.has("fake")).isFalse();
    assertThat(field(event, "log.level").asString()).isEqualTo("INFO");
    assertThat(field(event, "message").asString()).isEqualTo("user said: " + hostile);
    assertThat(field(event, "request_id").asString()).isEqualTo(hostile);
  }

  @Test
  void stackTracesAreBoundedByTheProdConfiguration() {
    Throwable deep = deepFailure(400);

    List<String> bounded;
    try (var capture = StructuredLogTestSupport.Capture.withProdConfig()) {
      bounded = capture.log(logger -> logger.error("failed", deep));
    }
    List<String> unbounded;
    try (var capture = new StructuredLogTestSupport.Capture(Map.of())) {
      unbounded = capture.log(logger -> logger.error("failed", deep));
    }

    String boundedTrace = field(single(bounded), "error.stack_trace").asString();
    String unboundedTrace = field(single(unbounded), "error.stack_trace").asString();
    assertThat(unboundedTrace.length()).isGreaterThan(8000);
    assertThat(boundedTrace.length()).isLessThanOrEqualTo(4096 + 64);
  }

  @Test
  void sensitiveValuesAreMaskedByTheProdConfiguration() {
    MDC.put("access_token", "abc123-TOKEN");

    List<String> lines;
    try (var capture = StructuredLogTestSupport.Capture.withProdConfig()) {
      lines =
          capture.log(logger -> logger.atInfo().addKeyValue("password", "hunter2").log("login"));
    }

    assertThat(lines.get(0)).doesNotContain("abc123-TOKEN").doesNotContain("hunter2");
  }

  private static Throwable deepFailure(int depth) {
    if (depth == 0) {
      return new IllegalStateException("bottom");
    }
    try {
      throw deepFailure(depth - 1);
    } catch (Throwable inner) {
      return new RuntimeException("level " + depth, inner);
    }
  }
}
