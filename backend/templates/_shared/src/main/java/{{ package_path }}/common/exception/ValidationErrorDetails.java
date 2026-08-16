package {{ base_package }}.common.exception;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Error payload for request-validation failures (Bean Validation constraint violations on
 * {@code @Valid} request bodies), extending the plain {@link ErrorDetails} shape with {@code
 * fieldErrors}: a map of field name to the list of validation messages for that field, so clients
 * can highlight individual invalid fields rather than parsing a single message string. Built by
 * {@link GlobalExceptionHandler#handleValidation} for HTTP 400 responses.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ValidationErrorDetails {

  private String code;
  private String message;
  private Map<String, List<String>> fieldErrors;
  private Instant timestamp;
}
