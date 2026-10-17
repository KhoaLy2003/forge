{%- set e = entity -%}
{%- set many = e.owning_relations | selectattr('is_collection') | list -%}
{%- set plural = e.plural_path -%}
{#- A request is invalid when it lacks a required scalar field (without default) or a required relation. -#}
{%- set required_scalars = e.fields | selectattr('required') | rejectattr('default_sql') | list -%}
{%- set required_relations = e.owning_relations | selectattr('required') | list -%}
{%- set can_be_invalid = required_scalars or required_relations -%}
{%- set imps = [
  base_package ~ '.common.dto.PageResponse',
  base_package ~ '.common.dto.PaginationMeta',
  base_package ~ '.common.exception.GlobalExceptionHandler',
  base_package ~ '.common.exception.ResourceNotFoundException',
  base_package ~ '.' ~ e.package ~ '.dto.Create' ~ e.name ~ 'Request',
  base_package ~ '.' ~ e.package ~ '.dto.' ~ e.name ~ 'Response',
  base_package ~ '.' ~ e.package ~ '.dto.Update' ~ e.name ~ 'Request',
  base_package ~ '.' ~ e.package ~ '.service.' ~ e.name ~ 'Service',
  'java.time.Instant',
  'java.util.List',
  'java.util.UUID',
  'org.junit.jupiter.api.Test',
  'org.springframework.beans.factory.annotation.Autowired',
  'org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc',
  'org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest',
  'org.springframework.context.annotation.Import',
  'org.springframework.http.MediaType',
  'org.springframework.test.context.bean.override.mockito.MockitoBean',
  'org.springframework.test.web.servlet.MockMvc',
  'tools.jackson.databind.ObjectMapper'] -%}
{%- if many %}{% set _ = imps.append('java.util.Set') %}{% endif -%}
{%- for f in e.fields -%}
{%- for i in f.imports %}{% set _ = imps.append(i) %}{% endfor -%}
{%- if f.is_enum %}{% set _ = imps.append(base_package ~ '.' ~ f.enum_import_suffix) %}{% endif -%}
{%- endfor -%}
{#- statements filling every scalar field with a sample value -#}
{%- macro fill(obj, alt) -%}
{%- for f in e.fields %}
    {{ obj }}.{{ f.setter }}({{ f.sample_value_alt if alt else f.sample_value }});
{%- endfor %}
{%- endmacro -%}
{#- statements filling the relation ids of a request -#}
{%- macro fill_ids(obj) -%}
{%- for r in e.owning_relations %}
{%- if r.is_collection %}
    {{ obj }}.set{{ r.id_field[:1] | upper }}{{ r.id_field[1:] }}(Set.of(UUID.randomUUID()));
{%- else %}
    {{ obj }}.set{{ r.id_field[:1] | upper }}{{ r.id_field[1:] }}(UUID.randomUUID());
{%- endif %}
{%- endfor %}
{%- endmacro -%}
package {{ base_package }}.{{ e.package }}.controller;

import static org.hamcrest.Matchers.containsString;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
{% if can_be_invalid -%}
import static org.mockito.Mockito.verifyNoInteractions;
{% endif -%}
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

{% for i in imps | unique(case_sensitive=true) | sort(case_sensitive=true) -%}
import {{ i }};
{% endfor %}
@WebMvcTest({{ e.name }}Controller.class)
@Import(GlobalExceptionHandler.class)
@AutoConfigureMockMvc(addFilters = false)
class {{ e.name }}ControllerTest {

  private static final String BASE_URL = "/api/v1/{{ plural }}";

  @Autowired private MockMvc mockMvc;

  @Autowired private ObjectMapper objectMapper;

  @MockitoBean private {{ e.name }}Service service;

  @Test
  void findById_whenFound_returns200WithEnvelope() throws Exception {
    UUID id = UUID.randomUUID();
    when(service.findById(id)).thenReturn(response(id));

    mockMvc
        .perform(get(BASE_URL + "/{id}", id))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.success").value(true))
        .andExpect(jsonPath("$.data.id").value(id.toString()));
  }

  @Test
  void findById_whenServiceThrowsNotFound_returns404() throws Exception {
    UUID id = UUID.randomUUID();
    when(service.findById(id)).thenThrow(new ResourceNotFoundException("not found"));

    mockMvc.perform(get(BASE_URL + "/{id}", id)).andExpect(status().isNotFound());
  }
{%- if can_be_invalid %}

  @Test
  void create_withoutRequiredValues_returns400() throws Exception {
    Create{{ e.name }}Request request = new Create{{ e.name }}Request();

    mockMvc
        .perform(
            post(BASE_URL)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
        .andExpect(status().isBadRequest());

    verifyNoInteractions(service);
  }
{%- endif %}

  @Test
  void create_whenValid_returns201WithLocationHeader() throws Exception {
    UUID id = UUID.randomUUID();
    when(service.create(any())).thenReturn(response(id));

    mockMvc
        .perform(
            post(BASE_URL)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(createRequest())))
        .andExpect(status().isCreated())
        .andExpect(header().string("Location", containsString(id.toString())))
        .andExpect(jsonPath("$.data.id").value(id.toString()));
  }

  @Test
  void findAll_returns200WithPagedEnvelope() throws Exception {
    UUID id = UUID.randomUUID();
    PageResponse<{{ e.name }}Response> page =
        PageResponse.<{{ e.name }}Response>builder()
            .data(List.of(response(id)))
            .pagination(PaginationMeta.builder().page(0).limit(20).total(1).totalPages(1).build())
            .build();
    when(service.findAll(0, 20, "createdAt", "DESC")).thenReturn(page);

    mockMvc
        .perform(get(BASE_URL))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.success").value(true))
        .andExpect(jsonPath("$.data.data[0].id").value(id.toString()));
  }

  @Test
  void update_whenValid_returns200WithUpdatedEnvelope() throws Exception {
    UUID id = UUID.randomUUID();
    when(service.update(eq(id), any())).thenReturn(response(id));

    mockMvc
        .perform(
            put(BASE_URL + "/{id}", id)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(updateRequest())))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.data.id").value(id.toString()));
  }

  @Test
  void delete_whenValid_returns204() throws Exception {
    UUID id = UUID.randomUUID();

    mockMvc.perform(delete(BASE_URL + "/{id}", id)).andExpect(status().isNoContent());
  }

  private static {{ e.name }}Response response(UUID id) {
    {{ e.name }}Response response = new {{ e.name }}Response();
    response.setId(id);
{{- fill('response', false) }}
{%- for r in e.owning_relations %}
{%- if r.is_collection %}
    response.set{{ r.id_field[:1] | upper }}{{ r.id_field[1:] }}(Set.of(UUID.randomUUID()));
{%- else %}
    response.set{{ r.id_field[:1] | upper }}{{ r.id_field[1:] }}(UUID.randomUUID());
{%- endif %}
{%- endfor %}
    response.setCreatedAt(Instant.now());
    response.setUpdatedAt(Instant.now());
    response.setVersion(0L);
    return response;
  }

  private static Create{{ e.name }}Request createRequest() {
    Create{{ e.name }}Request request = new Create{{ e.name }}Request();
{{- fill('request', false) }}
{{- fill_ids('request') }}
    return request;
  }

  private static Update{{ e.name }}Request updateRequest() {
    Update{{ e.name }}Request request = new Update{{ e.name }}Request();
{{- fill('request', true) }}
{{- fill_ids('request') }}
    return request;
  }
}
