package {{ base_package }}.example.controller;

import static org.hamcrest.Matchers.containsString;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import {{ base_package }}.common.exception.GlobalExceptionHandler;
import {{ base_package }}.common.exception.ResourceNotFoundException;
import {{ base_package }}.example.dto.CreateExampleRequest;
import {{ base_package }}.example.dto.ExampleResponse;
import {{ base_package }}.example.entity.ExampleStatus;
import {{ base_package }}.example.service.ExampleService;
import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import tools.jackson.databind.ObjectMapper;

@WebMvcTest(ExampleController.class)
@Import(GlobalExceptionHandler.class)
@AutoConfigureMockMvc(addFilters = false)
class ExampleControllerTest {

  @Autowired private MockMvc mockMvc;

  @Autowired private ObjectMapper objectMapper;

  @MockitoBean private ExampleService service;

  @Test
  void findById_whenFound_returns200WithEnvelope() throws Exception {
    UUID id = UUID.randomUUID();
    ExampleResponse fixture =
        ExampleResponse.builder()
            .id(id)
            .name("Widget")
            .status(ExampleStatus.ACTIVE)
            .createdAt(Instant.now())
            .updatedAt(Instant.now())
            .version(0L)
            .build();
    when(service.findById(id)).thenReturn(fixture);

    mockMvc
        .perform(get("/api/v1/examples/{id}", id))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.success").value(true))
        .andExpect(jsonPath("$.data.id").value(id.toString()));
  }

  @Test
  void create_withBlankName_returns400() throws Exception {
    CreateExampleRequest request = CreateExampleRequest.builder().name("").build();

    mockMvc
        .perform(
            post("/api/v1/examples")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
        .andExpect(status().isBadRequest());

    verifyNoInteractions(service);
  }

  @Test
  void findById_whenServiceThrowsNotFound_returns404() throws Exception {
    UUID id = UUID.randomUUID();
    when(service.findById(id)).thenThrow(new ResourceNotFoundException("not found"));

    mockMvc.perform(get("/api/v1/examples/{id}", id)).andExpect(status().isNotFound());
  }

  @Test
  void create_whenValid_returns201WithLocationHeader() throws Exception {
    UUID id = UUID.randomUUID();
    ExampleResponse fixture =
        ExampleResponse.builder()
            .id(id)
            .name("Widget")
            .status(ExampleStatus.ACTIVE)
            .createdAt(Instant.now())
            .updatedAt(Instant.now())
            .version(0L)
            .build();
    when(service.create(any())).thenReturn(fixture);

    CreateExampleRequest request = CreateExampleRequest.builder().name("Widget").build();

    mockMvc
        .perform(
            post("/api/v1/examples")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
        .andExpect(status().isCreated())
        .andExpect(header().string("Location", containsString(id.toString())))
        .andExpect(jsonPath("$.data.id").value(id.toString()));
  }
}
