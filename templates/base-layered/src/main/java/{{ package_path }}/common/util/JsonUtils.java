package {{ base_package }}.common.util;

import java.util.Optional;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.ObjectMapper;

/**
 * Best-effort JSON conversion helpers for call sites (typically logging and diagnostics) that must
 * never fail because of a serialization problem.
 *
 * <p>This is a Spring-managed component rather than a static utility class, unlike the rest of this
 * package, because it delegates to the application's configured {@link ObjectMapper} bean instead
 * of constructing its own. Using the injected bean means any Jackson customization registered
 * elsewhere in the application (custom modules, naming strategies, date formats, etc.) is respected
 * here too, rather than this class silently applying different defaults.
 */
@Component
@Slf4j
@RequiredArgsConstructor
public class JsonUtils {

  private final ObjectMapper objectMapper;

  /**
   * Serializes {@code value} to a JSON string, never throwing.
   *
   * <p>Intended for logging/diagnostic call sites where a serialization bug must never break the
   * primary request flow. Any exception raised while serializing is logged at {@code ERROR} level
   * (including the value's class name for context) and swallowed.
   *
   * @param value the object to serialize; may be {@code null}
   * @return the JSON representation of {@code value}, or the literal string {@code "{}"} if
   *     serialization fails
   */
  public String toJsonSafely(Object value) {
    try {
      return objectMapper.writeValueAsString(value);
    } catch (JacksonException e) {
      log.error(
          "Failed to serialize value of type [{}] to JSON",
          value == null ? "null" : value.getClass().getName(),
          e);
      return "{}";
    }
  }

  /**
   * Deserializes {@code json} into an instance of {@code type}, never throwing.
   *
   * @param json the JSON string to parse; a {@code null}/blank value yields an empty result
   * @param type the target type to deserialize into
   * @param <T> the target type
   * @return an {@link Optional} containing the deserialized instance, or {@link Optional#empty()}
   *     if {@code json} is {@code null}/blank or deserialization fails
   */
  public <T> Optional<T> fromJsonSafely(String json, Class<T> type) {
    if (!StringUtils.hasText(json)) {
      log.warn("Cannot deserialize null/blank JSON into type [{}]", type.getName());
      return Optional.empty();
    }
    try {
      return Optional.ofNullable(objectMapper.readValue(json, type));
    } catch (JacksonException e) {
      log.warn("Failed to deserialize JSON into type [{}]: {}", type.getName(), json, e);
      return Optional.empty();
    }
  }
}
