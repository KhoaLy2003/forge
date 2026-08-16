package {{ base_package }}.common.exception;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.MediaType;
import org.springframework.orm.ObjectOptimisticLockingFailureException;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import tools.jackson.databind.ObjectMapper;

@WebMvcTest(controllers = GlobalExceptionHandlerTest.ProbeController.class)
@Import({GlobalExceptionHandler.class, GlobalExceptionHandlerTest.ProbeController.class})
class GlobalExceptionHandlerTest {

  @Autowired private MockMvc mockMvc;

  @Autowired private ObjectMapper objectMapper;

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
}
