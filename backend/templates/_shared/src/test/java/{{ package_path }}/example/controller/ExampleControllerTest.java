package {{ base_package }}.example.controller;

import static org.hamcrest.Matchers.containsString;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import {{ base_package }}.common.dto.PageResponse;
import {{ base_package }}.common.dto.PaginationMeta;
import {{ base_package }}.common.exception.GlobalExceptionHandler;
import {{ base_package }}.common.exception.ResourceNotFoundException;
import {{ base_package }}.example.dto.CreateExampleRequest;
import {{ base_package }}.example.dto.ExampleResponse;
import {{ base_package }}.example.dto.UpdateExampleRequest;
import {{ base_package }}.example.entity.ExampleStatus;
import {{ base_package }}.example.service.ExampleService;
import java.time.Instant;
import java.util.List;
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

  @Test
  void findAll_returns200WithPagedEnvelope() throws Exception {
    ExampleResponse fixture = ExampleResponse.builder().name("Widget").build();
    PageResponse<ExampleResponse> page =
        PageResponse.<ExampleResponse>builder()
            .data(List.of(fixture))
            .pagination(PaginationMeta.builder().page(0).limit(20).total(1).totalPages(1).build())
            .build();
    when(service.findAll(0, 20, "createdAt", "DESC", null)).thenReturn(page);

    mockMvc
        .perform(get("/api/v1/examples"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.success").value(true))
        .andExpect(jsonPath("$.data.data[0].name").value("Widget"));
  }

  @Test
  void update_whenValid_returns200WithUpdatedEnvelope() throws Exception {
    UUID id = UUID.randomUUID();
    ExampleResponse fixture =
        ExampleResponse.builder().id(id).name("Renamed").status(ExampleStatus.ARCHIVED).build();
    when(service.update(eq(id), any())).thenReturn(fixture);

    UpdateExampleRequest request =
        UpdateExampleRequest.builder().name("Renamed").status(ExampleStatus.ARCHIVED).build();

    mockMvc
        .perform(
            put("/api/v1/examples/{id}", id)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.data.name").value("Renamed"));
  }

  @Test
  void delete_whenValid_returns204() throws Exception {
    UUID id = UUID.randomUUID();

    mockMvc.perform(delete("/api/v1/examples/{id}", id)).andExpect(status().isNoContent());
  }
}
