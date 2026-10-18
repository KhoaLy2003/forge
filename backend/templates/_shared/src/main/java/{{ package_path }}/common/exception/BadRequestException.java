package {{ base_package }}.common.exception;

/**
 * Thrown by service code when a request is well-formed but violates a business rule that Bean
 * Validation cannot express. {@link GlobalExceptionHandler} maps it to HTTP 400. Field-level input
 * errors should use Bean Validation annotations instead, which produce per-field messages.
 */
public class BadRequestException extends RuntimeException {

  /**
   * Creates the exception.
   *
   * @param message a description for developers; it is not logged and is shown to the client
   */
  public BadRequestException(String message) {
    super(message);
  }
}
