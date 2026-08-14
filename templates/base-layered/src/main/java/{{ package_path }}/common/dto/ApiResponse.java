package {{ base_package }}.common.dto;

import {{ base_package }}.common.exception.ErrorDetails;
import {{ base_package }}.common.exception.GlobalExceptionHandler;
import {{ base_package }}.common.exception.ValidationErrorDetails;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Uniform envelope wrapping every controller response (success or failure) so API consumers always
 * deal with the same top-level shape: a {@code success} flag, a human-readable {@code message}, and
 * a {@code data} payload that is either the actual result or, on failure, error details (see {@link
 * ErrorDetails} and {@link GlobalExceptionHandler}).
 *
 * @param <T> the type of the payload carried in {@code data}
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ApiResponse<T> {

  private boolean success;
  private String message;
  private T data;

  /**
   * Builds a successful response carrying a data payload.
   *
   * @param message human-readable success message
   * @param data the result payload
   * @param <T> the payload type
   * @return a success-flagged {@link ApiResponse} wrapping {@code data}
   */
  public static <T> ApiResponse<T> success(String message, T data) {
    return ApiResponse.<T>builder().success(true).message(message).data(data).build();
  }

  /**
   * Builds a successful response with no data payload (e.g. for delete operations).
   *
   * @param message human-readable success message
   * @return a success-flagged {@link ApiResponse} with a {@code null} data payload
   */
  public static ApiResponse<Void> success(String message) {
    return ApiResponse.<Void>builder().success(true).message(message).build();
  }

  /**
   * Builds a failure response carrying error details.
   *
   * @param message human-readable error message
   * @param details error details payload, typically an {@link ErrorDetails} or {@link
   *     ValidationErrorDetails}
   * @param <T> the details payload type
   * @return a failure-flagged {@link ApiResponse} wrapping {@code details}
   */
  public static <T> ApiResponse<T> error(String message, T details) {
    return ApiResponse.<T>builder().success(false).message(message).data(details).build();
  }
}
