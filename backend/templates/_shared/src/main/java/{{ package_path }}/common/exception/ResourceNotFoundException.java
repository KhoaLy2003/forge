package {{ base_package }}.common.exception;

/**
 * Thrown by service code when a requested resource does not exist (e.g. lookup by id finds no row).
 * Translated by {@link GlobalExceptionHandler#handleNotFound} into an HTTP 404 response.
 */
public class ResourceNotFoundException extends RuntimeException {

  /**
   * @param message human-readable description of what was not found, surfaced in the API response
   */
  public ResourceNotFoundException(String message) {
    super(message);
  }
}
