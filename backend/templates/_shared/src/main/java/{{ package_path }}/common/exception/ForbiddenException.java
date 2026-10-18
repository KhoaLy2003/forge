package {{ base_package }}.common.exception;

/**
 * Thrown when the caller is identified but not allowed to perform the operation. {@link
 * GlobalExceptionHandler} maps it to HTTP 403. Use {@link UnauthorizedException} instead when there
 * is no identified caller at all.
 */
public class ForbiddenException extends RuntimeException {

  /**
   * Creates the exception.
   *
   * @param message a description for developers; it is not logged and is shown to the client
   */
  public ForbiddenException(String message) {
    super(message);
  }
}
