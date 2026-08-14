package {{ base_package }}.common.exception;

import {{ base_package }}.common.dto.ApiResponse;
import java.time.Instant;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Machine-readable error payload carried in the {@code data} field of an {@link ApiResponse#error}
 * response: a stable {@code code} clients can branch on, a human-readable {@code message}, and the
 * {@code timestamp} the error was produced. Built by {@link GlobalExceptionHandler} for every
 * non-validation failure.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ErrorDetails {

  private String code;
  private String message;
  private Instant timestamp;
}
