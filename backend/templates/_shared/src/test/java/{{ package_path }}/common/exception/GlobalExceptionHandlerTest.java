package {{ base_package }}.common.exception;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import java.sql.SQLException;
import java.util.Map;
import java.util.stream.Collectors;
import org.hibernate.exception.ConstraintViolationException;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.MediaType;
import org.springframework.orm.ObjectOptimisticLockingFailureException;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import tools.jackson.databind.ObjectMapper;

@WebMvcTest(
    controllers = {
      GlobalExceptionHandlerTest.ProbeController.class,
      GlobalExceptionHandlerTest.ParamProbeController.class,
      GlobalExceptionHandlerTest.MvcValidatedProbeController.class
    })
@Import({
  GlobalExceptionHandler.class,
  GlobalExceptionHandlerTest.ProbeController.class,
  GlobalExceptionHandlerTest.ParamProbeController.class,
  GlobalExceptionHandlerTest.MvcValidatedProbeController.class
})
class GlobalExceptionHandlerTest {

  @Autowired private MockMvc mockMvc;

  @Autowired private ObjectMapper objectMapper;

  private final Logger handlerLogger =
      (Logger) LoggerFactory.getLogger(GlobalExceptionHandler.class);
  private final ListAppender<ILoggingEvent> logs = new ListAppender<>();

  @BeforeEach
  void attachLogAppender() {
    logs.start();
    handlerLogger.addAppender(logs);
  }

  @AfterEach
  void detachLogAppender() {
    handlerLogger.detachAppender(logs);
  }

  private static Map<String, Object> fields(ILoggingEvent event) {
    if (event.getKeyValuePairs() == null) {
      return Map.of();
    }
    return event.getKeyValuePairs().stream()
        .collect(Collectors.toMap(kv -> kv.key, kv -> kv.value));
  }

  private String everythingLogged() {
    return logs.list.stream()
        .map(e -> e.getFormattedMessage() + fields(e))
        .collect(Collectors.joining(" | "));
  }

  @RestController
  static class ProbeController {
    @PostMapping("/probe/validate")
    String validate(@Valid @RequestBody ProbeRequest request) {
      return "ok";
    }

    @GetMapping("/probe/not-found")
    String notFound() {
      throw new ResourceNotFoundException("probe not found");
    }

    @GetMapping("/probe/conflict")
    String conflict() {
      throw new ConflictException("probe conflict");
    }

    @GetMapping("/probe/boom")
    String boom() {
      throw new RuntimeException("boom");
    }

    @GetMapping("/probe/optimistic-lock")
    String optimisticLock() {
      throw new ObjectOptimisticLockingFailureException("Example", "probe-id");
    }

    @GetMapping("/probe/data-integrity")
    String dataIntegrity() {
      throw new DataIntegrityViolationException("probe constraint violated");
    }

    @GetMapping("/probe/unauthorized")
    String unauthorized() {
      throw new UnauthorizedException("token for person@example.org has expired");
    }

    @GetMapping("/probe/forbidden")
    String forbidden() {
      throw new ForbiddenException("person@example.org may not do this");
    }

    @GetMapping("/probe/bad-request")
    String badRequest() {
      throw new BadRequestException("person@example.org is not a valid sort field");
    }

    @GetMapping("/probe/not-found-pii")
    String notFoundPii() {
      throw new ResourceNotFoundException("no account for person@example.org");
    }

    @GetMapping("/probe/conflict-pii")
    String conflictPii() {
      throw new ConflictException("person@example.org already exists");
    }

    @GetMapping("/probe/data-integrity-pii")
    String dataIntegrityPii() {
      throw new DataIntegrityViolationException(
          "could not execute statement: Key (email)=(person@example.org) already exists",
          new ConstraintViolationException(
              "duplicate key value",
              new SQLException("Key (email)=(person@example.org)"),
              "uk_account_email"));
    }
  }

  /** Class-level {@code @Validated} makes constraint annotations on parameters take effect. */
  @RestController
  @Validated
  static class ParamProbeController {
    @GetMapping("/probe/param")
    String param(
        @RequestParam @Min(1) @Max(100) int size, @RequestParam(defaultValue = "x") String name) {
      return "ok";
    }
  }

  /**
   * Without class-level {@code @Validated}, Spring MVC validates constraint annotations on
   * parameters itself and throws {@code HandlerMethodValidationException} instead.
   */
  @RestController
  static class MvcValidatedProbeController {
    @GetMapping("/probe/mvc-param")
    String param(@RequestParam @Min(1) int size) {
      return "ok";
    }
  }

  record ProbeRequest(@NotBlank String name) {}

  @Test
  void validate_withBlankName_returns400() throws Exception {
    mockMvc
        .perform(
            post("/probe/validate")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(new ProbeRequest(""))))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.success").value(false))
        .andExpect(jsonPath("$.data.fieldErrors.name").exists());
  }

  @Test
  void notFound_returns404() throws Exception {
    mockMvc
        .perform(get("/probe/not-found"))
        .andExpect(status().isNotFound())
        .andExpect(jsonPath("$.success").value(false))
        .andExpect(jsonPath("$.message").value("probe not found"));
  }

  @Test
  void conflict_returns409() throws Exception {
    mockMvc.perform(get("/probe/conflict")).andExpect(status().isConflict());
  }

  @Test
  void genericException_returns500() throws Exception {
    mockMvc
        .perform(get("/probe/boom"))
        .andExpect(status().isInternalServerError())
        .andExpect(jsonPath("$.message").value("An unexpected error occurred"));
  }

  @Test
  void optimisticLockFailure_returns409() throws Exception {
    mockMvc
        .perform(get("/probe/optimistic-lock"))
        .andExpect(status().isConflict())
        .andExpect(jsonPath("$.message").value("Conflict detected"))
        .andExpect(jsonPath("$.data.code").value("OPTIMISTIC_LOCK_CONFLICT"));
  }

  @Test
  void dataIntegrityViolation_returns409() throws Exception {
    mockMvc
        .perform(get("/probe/data-integrity"))
        .andExpect(status().isConflict())
        .andExpect(jsonPath("$.message").value("Data integrity constraint violated"))
        .andExpect(jsonPath("$.data.code").value("DATA_INTEGRITY_VIOLATION"));
  }

  @Test
  void notFound_logsOnceWithEventNameAndNoMessageContent() throws Exception {
    mockMvc.perform(get("/probe/not-found-pii")).andExpect(status().isNotFound());

    assertThat(logs.list).hasSize(1);
    assertThat(logs.list.get(0).getLevel()).isEqualTo(Level.WARN);
    assertThat(fields(logs.list.get(0))).containsEntry("event.name", "request.not_found");
    assertThat(everythingLogged()).doesNotContain("person@example.org");
  }

  @Test
  void unauthorized_returns401WithTheStandardEnvelope() throws Exception {
    mockMvc
        .perform(get("/probe/unauthorized"))
        .andExpect(status().isUnauthorized())
        .andExpect(jsonPath("$.success").value(false))
        .andExpect(jsonPath("$.data.code").value("UNAUTHORIZED"));
  }

  @Test
  void forbidden_returns403WithTheStandardEnvelopeAndLogsNoMessage() throws Exception {
    mockMvc
        .perform(get("/probe/forbidden"))
        .andExpect(status().isForbidden())
        .andExpect(jsonPath("$.success").value(false))
        .andExpect(jsonPath("$.data.code").value("FORBIDDEN"));

    assertThat(logs.list).hasSize(1);
    assertThat(fields(logs.list.get(0))).containsEntry("event.name", "request.forbidden");
    assertThat(everythingLogged()).doesNotContain("person@example.org");
  }

  @Test
  void badRequest_returns400WithTheStandardEnvelopeAndLogsNoMessage() throws Exception {
    mockMvc
        .perform(get("/probe/bad-request"))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.success").value(false))
        .andExpect(jsonPath("$.data.code").value("BAD_REQUEST"));

    assertThat(logs.list).hasSize(1);
    assertThat(fields(logs.list.get(0))).containsEntry("event.name", "request.bad_request");
    assertThat(everythingLogged()).doesNotContain("person@example.org");
  }

  @Test
  void unauthorized_logsOnceWithEventNameAndNeverTheExceptionMessage() throws Exception {
    mockMvc.perform(get("/probe/unauthorized")).andExpect(status().isUnauthorized());

    assertThat(logs.list).hasSize(1);
    assertThat(logs.list.get(0).getLevel()).isEqualTo(Level.WARN);
    assertThat(fields(logs.list.get(0))).containsEntry("event.name", "request.unauthorized");
    assertThat(everythingLogged()).doesNotContain("person@example.org");
  }

  @Test
  void conflict_logsOnceWithEventNameAndNoMessageContent() throws Exception {
    mockMvc.perform(get("/probe/conflict-pii")).andExpect(status().isConflict());

    assertThat(logs.list).hasSize(1);
    assertThat(fields(logs.list.get(0))).containsEntry("event.name", "request.conflict");
    assertThat(everythingLogged()).doesNotContain("person@example.org");
  }

  @Test
  void validationFailure_logsFieldNamesButNeverValues() throws Exception {
    mockMvc
        .perform(
            post("/probe/validate")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"name\":\"\"}"))
        .andExpect(status().isBadRequest());

    assertThat(logs.list).hasSize(1);
    assertThat(logs.list.get(0).getLevel()).isEqualTo(Level.INFO);
    assertThat(fields(logs.list.get(0))).containsEntry("event.name", "request.validation.failed");
    assertThat(everythingLogged()).contains("name");
  }

  @Test
  void optimisticLock_logsOnceWithEventName() throws Exception {
    mockMvc.perform(get("/probe/optimistic-lock")).andExpect(status().isConflict());

    assertThat(logs.list).hasSize(1);
    assertThat(fields(logs.list.get(0)))
        .containsEntry("event.name", "request.optimistic_lock.failed");
    assertThat(everythingLogged()).doesNotContain("probe-id");
  }

  @Test
  void dataIntegrityViolation_logsConstraintNameButNeverTheOffendingValue() throws Exception {
    mockMvc.perform(get("/probe/data-integrity-pii")).andExpect(status().isConflict());

    assertThat(logs.list).hasSize(1);
    ILoggingEvent event = logs.list.get(0);
    assertThat(fields(event))
        .containsEntry("event.name", "request.data_integrity.violated")
        .containsEntry("db.constraint", "uk_account_email");
    assertThat(everythingLogged()).doesNotContain("person@example.org");
    assertThat(event.getThrowableProxy()).isNull();
  }

  @Test
  void dataIntegrityViolation_withoutAKnownConstraintLogsUnknown() throws Exception {
    mockMvc.perform(get("/probe/data-integrity")).andExpect(status().isConflict());

    assertThat(logs.list).hasSize(1);
    assertThat(fields(logs.list.get(0))).containsEntry("db.constraint", "unknown");
  }

  @Test
  void requestParameterConstraintViolation_returns400WithTheFieldName() throws Exception {
    mockMvc
        .perform(get("/probe/param").param("size", "0"))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.success").value(false))
        .andExpect(jsonPath("$.data.code").value("VALIDATION_FAILED"))
        .andExpect(jsonPath("$.data.fieldErrors.size").isNotEmpty());
  }

  @Test
  void requestParameterTooLarge_returns400() throws Exception {
    mockMvc.perform(get("/probe/param").param("size", "101")).andExpect(status().isBadRequest());
  }

  @Test
  void mvcValidatedParameterViolation_returns400WithTheParameterName() throws Exception {
    mockMvc
        .perform(get("/probe/mvc-param").param("size", "0"))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.data.code").value("VALIDATION_FAILED"))
        .andExpect(jsonPath("$.data.fieldErrors.size").isNotEmpty());
  }

  @Test
  void mvcValidatedParameterViolation_logsOnceAtInfoWithFieldNamesOnly() throws Exception {
    mockMvc.perform(get("/probe/mvc-param").param("size", "0")).andExpect(status().isBadRequest());

    assertThat(logs.list).hasSize(1);
    assertThat(fields(logs.list.get(0))).containsEntry("event.name", "request.validation.failed");
    assertThat(fields(logs.list.get(0)).get("validation.fields").toString()).isEqualTo("size");
  }

  @Test
  void requestParameterWithinRange_isAccepted() throws Exception {
    mockMvc.perform(get("/probe/param").param("size", "5")).andExpect(status().isOk());
  }

  @Test
  void requestParameterConstraintViolation_logsOnceAtInfoWithFieldNamesOnly() throws Exception {
    mockMvc.perform(get("/probe/param").param("size", "0")).andExpect(status().isBadRequest());

    assertThat(logs.list).hasSize(1);
    assertThat(logs.list.get(0).getLevel()).isEqualTo(Level.INFO);
    assertThat(fields(logs.list.get(0))).containsEntry("event.name", "request.validation.failed");
    assertThat(fields(logs.list.get(0)).get("validation.fields").toString()).contains("size");
  }

  @Test
  void unexpectedException_logsOnceAtErrorWithTheStackTraceAndEventName() throws Exception {
    mockMvc.perform(get("/probe/boom")).andExpect(status().isInternalServerError());

    assertThat(logs.list).hasSize(1);
    ILoggingEvent event = logs.list.get(0);
    assertThat(event.getLevel()).isEqualTo(Level.ERROR);
    assertThat(fields(event)).containsEntry("event.name", "request.unexpected");
    assertThat(event.getThrowableProxy()).isNotNull();
  }
}
