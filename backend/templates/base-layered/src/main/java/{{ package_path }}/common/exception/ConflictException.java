package {{ base_package }}.common.exception;

/**
 * Thrown by service code when a request conflicts with the current state of a resource (e.g. a
 * uniqueness constraint or business-rule conflict detected before hitting the database). Translated
 * by {@link GlobalExceptionHandler#handleConflict} into an HTTP 409 response.
 */
public class ConflictException extends RuntimeException {

  /**
   * @param message human-readable description of the conflict, surfaced in the API response
   */
  public ConflictException(String message) {
    super(message);
  }
}
