package {{ base_package }}.common.config;

import java.util.regex.Pattern;
import org.springframework.boot.json.JsonWriter;
import org.springframework.boot.logging.structured.StructuredLoggingJsonMembersCustomizer;

/**
 * Masks the value of any structured-log member whose name looks sensitive (password, secret, token,
 * authorization, cookie, api key) before the line is written, so such values never reach stdout or
 * the log store even if code passes them to a logger by mistake.
 *
 * <p>This is a safety net, not a licence to log sensitive data: free-text {@code message} content
 * is not scanned, so callers must still never put credentials or personal data into messages. It is
 * not a Spring bean on purpose - Spring Boot instantiates it by class name while logging starts,
 * before the application context exists - and is enabled through {@code
 * logging.structured.json.customizer} in {@code application-prod.yml}.
 *
 * <p>Both MDC entries and {@code addKeyValue} pairs are members of the JSON object, so both are
 * covered; every segment of a nested member path is checked.
 */
public class SensitiveDataCustomizer implements StructuredLoggingJsonMembersCustomizer<Object> {

  /** The replacement written instead of a sensitive value. */
  static final String MASK = "***";

  private static final Pattern SENSITIVE =
      Pattern.compile("(?i).*(pass(word)?|secret|token|authorization|cookie|api[_-]?key).*");

  /** {@inheritDoc} */
  @Override
  public void customize(JsonWriter.Members<Object> members) {
    members.applyingValueProcessor(
        (JsonWriter.ValueProcessor<Object>)
            (path, value) -> isSensitive(path) && value != null ? MASK : value);
  }

  private static boolean isSensitive(JsonWriter.MemberPath path) {
    for (JsonWriter.MemberPath current = path; current != null; current = current.parent()) {
      String name = current.name();
      if (name != null && SENSITIVE.matcher(name).matches()) {
        return true;
      }
    }
    return false;
  }
}
