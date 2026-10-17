package {{ base_package }}.common.config;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;

class SensitiveDataCustomizerTest {

  private static final Map<String, String> WITH_CUSTOMIZER =
      Map.of("logging.structured.json.customizer", SensitiveDataCustomizer.class.getName());

  @AfterEach
  void cleanMdc() {
    MDC.clear();
  }

  @Test
  void masksSensitiveMdcAndKeyValueMembersAndKeepsTheRest() {
    MDC.put("access_token", "abc123-TOKEN");
    MDC.put("tenant", "acme");

    List<String> lines;
    try (var capture = new StructuredLogTestSupport.Capture(WITH_CUSTOMIZER)) {
      lines =
          capture.log(
              logger ->
                  logger
                      .atInfo()
                      .addKeyValue("password", "hunter2-SECRET")
                      .addKeyValue("Authorization", "Bearer XYZ-HEADER")
                      .addKeyValue("order_id", "o-42")
                      .log("user signed in"));
    }

    assertThat(lines).hasSize(1);
    String line = lines.get(0);
    assertThat(line)
        .doesNotContain("abc123-TOKEN")
        .doesNotContain("hunter2-SECRET")
        .doesNotContain("Bearer XYZ-HEADER")
        .contains("***")
        .contains("acme")
        .contains("o-42")
        .contains("user signed in");
  }

  @Test
  void withoutTheCustomizerTheSameValuesWouldBeLogged() {
    MDC.put("access_token", "abc123-TOKEN");

    List<String> lines;
    try (var capture = new StructuredLogTestSupport.Capture(Map.of())) {
      lines = capture.log(logger -> logger.atInfo().addKeyValue("password", "hunter2").log("x"));
    }

    assertThat(lines.get(0)).contains("abc123-TOKEN").contains("hunter2");
  }
}
