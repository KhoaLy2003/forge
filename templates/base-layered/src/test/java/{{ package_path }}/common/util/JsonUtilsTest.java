package {{ base_package }}.common.util;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.json.JsonMapper;

class JsonUtilsTest {

  private JsonUtils jsonUtils;

  @BeforeEach
  void setUp() {
    ObjectMapper objectMapper = JsonMapper.builder().build();
    jsonUtils = new JsonUtils(objectMapper);
  }

  record Widget(String name, int quantity) {}

  @Test
  void toJsonSafely_serializesSimplePojo() {
    String json = jsonUtils.toJsonSafely(new Widget("bolt", 5));

    assertThat(json).isEqualTo("{\"name\":\"bolt\",\"quantity\":5}");
  }

  @Test
  void toJsonSafely_withNullValue_returnsJsonNullLiteral() {
    String json = jsonUtils.toJsonSafely(null);

    assertThat(json).isEqualTo("null");
  }

  @Test
  void fromJsonSafely_withValidJson_returnsPopulatedOptional() {
    Optional<Widget> result =
        jsonUtils.fromJsonSafely("{\"name\":\"bolt\",\"quantity\":5}", Widget.class);

    assertThat(result).contains(new Widget("bolt", 5));
  }

  @Test
  void fromJsonSafely_withMalformedJson_returnsEmptyOptional() {
    Optional<Widget> result = jsonUtils.fromJsonSafely("{not-valid-json", Widget.class);

    assertThat(result).isEmpty();
  }

  @Test
  void fromJsonSafely_withNullInput_returnsEmptyOptional() {
    Optional<Widget> result = jsonUtils.fromJsonSafely(null, Widget.class);

    assertThat(result).isEmpty();
  }

  @Test
  void fromJsonSafely_withBlankInput_returnsEmptyOptional() {
    Optional<Widget> result = jsonUtils.fromJsonSafely("   ", Widget.class);

    assertThat(result).isEmpty();
  }
}
