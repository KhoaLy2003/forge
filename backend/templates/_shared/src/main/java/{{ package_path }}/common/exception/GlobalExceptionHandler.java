package {{ base_package }}.common.exception;

import {{ base_package }}.common.dto.ApiResponse;
import {{ base_package }}.common.entity.BaseEntity;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;
import lombok.extern.slf4j.Slf4j;
import org.hibernate.exception.ConstraintViolationException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.orm.ObjectOptimisticLockingFailureException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.HandlerMethodValidationException;

/**
 * Central exception-to-HTTP-response translation for every controller in the application.
 *
 * <p>Rather than having each controller catch and format its own errors, all thrown exceptions
 * bubble up to this {@code @RestControllerAdvice}, which maps each known exception type to a
 * consistent HTTP status and an {@link ApiResponse#error} envelope. This keeps controllers and
 * services free of response-formatting concerns and guarantees every error response — expected or
 * not — has the same shape.
 */
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

  /**
   * Logs an expected client error once, with a stable event name and the exception type only. The
   * exception message is deliberately not logged: service code may put user-supplied values (an
   * email, a name) into it, and the route is already recorded by the request log.
   */
  private static void logClientError(String eventName, String message, Exception ex) {
    log.atWarn()
        .addKeyValue("event.name", eventName)
        .addKeyValue("error.type", ex.getClass().getSimpleName())
        .log(message);
  }

  /** Finds the violated constraint's name in the cause chain, or {@code "unknown"}. */
  private static String constraintName(Throwable ex) {
    for (Throwable cause = ex; cause != null; cause = cause.getCause()) {
      if (cause instanceof ConstraintViolationException violation
          && violation.getConstraintName() != null) {
        return violation.getConstraintName();
      }
    }
    return "unknown";
  }

  /**
   * Handles {@link ResourceNotFoundException}, thrown by service code (e.g. {@code
   * ExampleServiceImpl}) when a lookup by id finds no matching, non-deleted row.
   *
   * @param ex the thrown exception, whose message is surfaced to the client
   * @return an HTTP 404 response wrapping {@link ErrorDetails}
   */
  @ExceptionHandler(ResourceNotFoundException.class)
  public ResponseEntity<ApiResponse<ErrorDetails>> handleNotFound(ResourceNotFoundException ex) {
    logClientError("request.not_found", "Resource not found", ex);
    ErrorDetails details =
        ErrorDetails.builder()
            .code("RESOURCE_NOT_FOUND")
            .message(ex.getMessage())
            .timestamp(Instant.now())
            .build();
    return ResponseEntity.status(HttpStatus.NOT_FOUND)
        .body(ApiResponse.error(ex.getMessage(), details));
  }

  /**
   * Handles {@link UnauthorizedException}, thrown when an endpoint needs an authenticated caller
   * and there is none.
   *
   * @param ex the thrown exception, whose message is surfaced to the client
   * @return an HTTP 401 response wrapping {@link ErrorDetails}
   */
  @ExceptionHandler(UnauthorizedException.class)
  public ResponseEntity<ApiResponse<ErrorDetails>> handleUnauthorized(UnauthorizedException ex) {
    logClientError("request.unauthorized", "Unauthorized", ex);
    ErrorDetails details =
        ErrorDetails.builder()
            .code("UNAUTHORIZED")
            .message(ex.getMessage())
            .timestamp(Instant.now())
            .build();
    return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
        .body(ApiResponse.error(ex.getMessage(), details));
  }

  /**
   * Handles {@link ConflictException}, thrown by service code (e.g. {@code ExampleServiceImpl})
   * when a request conflicts with a business rule or existing state before any database constraint
   * is reached.
   *
   * @param ex the thrown exception, whose message is surfaced to the client
   * @return an HTTP 409 response wrapping {@link ErrorDetails}
   */
  @ExceptionHandler(ConflictException.class)
  public ResponseEntity<ApiResponse<ErrorDetails>> handleConflict(ConflictException ex) {
    logClientError("request.conflict", "Conflict", ex);
    ErrorDetails details =
        ErrorDetails.builder()
            .code("CONFLICT")
            .message(ex.getMessage())
            .timestamp(Instant.now())
            .build();
    return ResponseEntity.status(HttpStatus.CONFLICT)
        .body(ApiResponse.error(ex.getMessage(), details));
  }

  /**
   * Handles {@link MethodArgumentNotValidException}, thrown automatically by Spring MVC when a
   * {@code @Valid}-annotated request body fails Bean Validation (e.g. a blank required field on the
   * {@code Example} create/update request). Field-level violations are collected into a
   * field-name-to-messages map so clients can highlight individual invalid inputs.
   *
   * @param ex the thrown exception, whose binding result supplies the field errors
   * @return an HTTP 400 response wrapping {@link ValidationErrorDetails}
   */
  @ExceptionHandler(MethodArgumentNotValidException.class)
  public ResponseEntity<ApiResponse<ValidationErrorDetails>> handleValidation(
      MethodArgumentNotValidException ex) {
    Map<String, List<String>> fieldErrors = new HashMap<>();
    ex.getBindingResult()
        .getFieldErrors()
        .forEach(
            error ->
                fieldErrors
                    .computeIfAbsent(error.getField(), k -> new ArrayList<>())
                    .add(error.getDefaultMessage()));
    return validationFailed(fieldErrors);
  }

  /**
   * Handles {@link jakarta.validation.ConstraintViolationException}, thrown when a constraint such
   * as {@code @Min} or {@code @Max} on a request parameter or path variable of a {@code @Validated}
   * controller is violated (for example {@code size=0} on a paged list).
   *
   * @param ex the thrown exception, whose violations supply the parameter names and messages
   * @return an HTTP 400 response wrapping {@link ValidationErrorDetails}
   */
  @ExceptionHandler(jakarta.validation.ConstraintViolationException.class)
  public ResponseEntity<ApiResponse<ValidationErrorDetails>> handleConstraintViolation(
      jakarta.validation.ConstraintViolationException ex) {
    Map<String, List<String>> fieldErrors = new HashMap<>();
    ex.getConstraintViolations()
        .forEach(
            violation -> {
              String name = null;
              for (jakarta.validation.Path.Node node : violation.getPropertyPath()) {
                name = node.getName();
              }
              fieldErrors
                  .computeIfAbsent(name == null ? "parameter" : name, k -> new ArrayList<>())
                  .add(violation.getMessage());
            });
    return validationFailed(fieldErrors);
  }

  /**
   * Handles {@link HandlerMethodValidationException}, which Spring MVC throws for constraint
   * violations on controller method parameters when it performs the validation itself (a controller
   * without class-level {@code @Validated}).
   *
   * @param ex the thrown exception, whose parameter results supply the names and messages
   * @return an HTTP 400 response wrapping {@link ValidationErrorDetails}
   */
  @ExceptionHandler(HandlerMethodValidationException.class)
  public ResponseEntity<ApiResponse<ValidationErrorDetails>> handleMethodValidation(
      HandlerMethodValidationException ex) {
    Map<String, List<String>> fieldErrors = new HashMap<>();
    ex.getParameterValidationResults()
        .forEach(
            result -> {
              String name = result.getMethodParameter().getParameterName();
              result
                  .getResolvableErrors()
                  .forEach(
                      error ->
                          fieldErrors
                              .computeIfAbsent(
                                  name == null ? "parameter" : name, k -> new ArrayList<>())
                              .add(error.getDefaultMessage()));
            });
    return validationFailed(fieldErrors);
  }

  /**
   * Logs a validation failure once (field names only - submitted values may be personal data) and
   * builds the HTTP 400 response.
   */
  private ResponseEntity<ApiResponse<ValidationErrorDetails>> validationFailed(
      Map<String, List<String>> fieldErrors) {
    log.atInfo()
        .addKeyValue("event.name", "request.validation.failed")
        .addKeyValue("validation.fields", String.join(",", new TreeSet<>(fieldErrors.keySet())))
        .log("Request validation failed");
    ValidationErrorDetails details =
        ValidationErrorDetails.builder()
            .code("VALIDATION_FAILED")
            .message("Request validation failed")
            .fieldErrors(fieldErrors)
            .timestamp(Instant.now())
            .build();
    return ResponseEntity.status(HttpStatus.BAD_REQUEST)
        .body(ApiResponse.error("Validation failed", details));
  }

  /**
   * Handles {@link ObjectOptimisticLockingFailureException}, thrown by Hibernate when an update
   * targets an entity whose {@code @Version} (from {@link BaseEntity}) no longer matches the row in
   * the database — i.e. another request modified or deleted the row concurrently.
   *
   * @param ex the thrown exception; its own message is not surfaced, a generic conflict message is
   *     returned instead
   * @return an HTTP 409 response wrapping {@link ErrorDetails}
   */
  @ExceptionHandler(ObjectOptimisticLockingFailureException.class)
  public ResponseEntity<ApiResponse<ErrorDetails>> handleOptimisticLock(
      ObjectOptimisticLockingFailureException ex) {
    log.atWarn()
        .addKeyValue("event.name", "request.optimistic_lock.failed")
        .addKeyValue("error.type", ex.getClass().getSimpleName())
        .log("Optimistic locking failure");
    ErrorDetails details =
        ErrorDetails.builder()
            .code("OPTIMISTIC_LOCK_CONFLICT")
            .message("The resource was modified by another request")
            .timestamp(Instant.now())
            .build();
    return ResponseEntity.status(HttpStatus.CONFLICT)
        .body(ApiResponse.error("Conflict detected", details));
  }

  /**
   * Handles {@link DataIntegrityViolationException}, thrown when a persistence operation violates a
   * database-level constraint (e.g. a unique or foreign-key constraint) that wasn't caught by Bean
   * Validation beforehand.
   *
   * @param ex the thrown exception; its own message is not surfaced, a generic message is returned
   *     instead to avoid leaking database schema details
   * @return an HTTP 409 response wrapping {@link ErrorDetails}
   */
  @ExceptionHandler(DataIntegrityViolationException.class)
  public ResponseEntity<ApiResponse<ErrorDetails>> handleDataIntegrityViolation(
      DataIntegrityViolationException ex) {
    // The driver message embeds the offending values (for example "Key (email)=(a@b.c)"), so only
    // the constraint name is logged.
    log.atError()
        .addKeyValue("event.name", "request.data_integrity.violated")
        .addKeyValue("db.constraint", constraintName(ex))
        .log("Data integrity violation");
    ErrorDetails details =
        ErrorDetails.builder()
            .code("DATA_INTEGRITY_VIOLATION")
            .message("Data integrity constraint violated")
            .timestamp(Instant.now())
            .build();
    return ResponseEntity.status(HttpStatus.CONFLICT)
        .body(ApiResponse.error("Data integrity constraint violated", details));
  }

  /**
   * Catch-all handler for any exception not matched by a more specific handler above, guaranteeing
   * the API never leaks an unformatted stack trace or default container error page to clients. Logs
   * the full exception for diagnosis, since the response intentionally omits implementation
   * details.
   *
   * @param ex the thrown exception; its own message is not surfaced, a generic message is returned
   *     instead
   * @return an HTTP 500 response wrapping {@link ErrorDetails}
   */
  @ExceptionHandler(Exception.class)
  public ResponseEntity<ApiResponse<ErrorDetails>> handleGeneric(Exception ex) {
    log.atError()
        .addKeyValue("event.name", "request.unexpected")
        .setCause(ex)
        .log("Unexpected error occurred");
    ErrorDetails details =
        ErrorDetails.builder()
            .code("INTERNAL_SERVER_ERROR")
            .message("An unexpected error occurred")
            .timestamp(Instant.now())
            .build();
    return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
        .body(ApiResponse.error("An unexpected error occurred", details));
  }
}
