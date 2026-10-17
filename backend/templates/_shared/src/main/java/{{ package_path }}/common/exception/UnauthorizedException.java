package {{ base_package }}.common.exception;

/**
 * Thrown when a request needs an authenticated caller and there is none. {@link
 * GlobalExceptionHandler} maps it to HTTP 401. The generated project has no authentication of its
 * own; code that needs a caller (for example the notification inbox) throws this until the project
 * wires its authentication in.
 */
public class UnauthorizedException extends RuntimeException {

  /**
   * Creates the exception.
   *
   * @param message a description for developers; it is not logged and is shown to the client
   */
  public UnauthorizedException(String message) {
    super(message);
  }
}
