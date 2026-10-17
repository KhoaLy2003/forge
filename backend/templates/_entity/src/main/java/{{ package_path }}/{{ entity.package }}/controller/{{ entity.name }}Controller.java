{%- set e = entity -%}
{%- set plural = e.plural_path | replace('-', ' ') | capitalize -%}
{#- Line(s) for `head + args + tail`, wrapped like google-java-format: one line, else all arguments on
    one continuation line, else one per line. -#}
{%- macro wrap(indent, head, args, tail) -%}
{%- set pad = ' ' * indent -%}
{%- set joined = args | join(', ') -%}
{%- if (pad ~ head ~ joined ~ tail) | length <= 100 -%}
{{ pad ~ head ~ joined ~ tail }}
{%- elif (pad ~ '    ' ~ joined ~ tail) | length <= 100 -%}
{{ pad ~ head }}
{{ pad ~ '    ' ~ joined ~ tail }}
{%- else -%}
{{ pad ~ head }}
{%- for a in args %}
{{ pad ~ '    ' ~ a ~ (',' if not loop.last else tail) }}
{%- endfor -%}
{%- endif -%}
{%- endmacro -%}
{#- `decl = rhs;` on one line, else broken after the `=`. -#}
{%- macro assign(indent, decl, rhs) -%}
{%- set pad = ' ' * indent -%}
{%- if (pad ~ decl ~ ' = ' ~ rhs ~ ';') | length <= 100 -%}
{{ pad ~ decl ~ ' = ' ~ rhs ~ ';' }}
{%- else -%}
{{ pad ~ decl ~ ' =' }}
{{ pad ~ '    ' ~ rhs ~ ';' }}
{%- endif -%}
{%- endmacro -%}
{%- set imps = [
  base_package ~ '.common.dto.ApiResponse',
  base_package ~ '.common.dto.PageResponse',
  base_package ~ '.' ~ e.package ~ '.dto.Create' ~ e.name ~ 'Request',
  base_package ~ '.' ~ e.package ~ '.dto.' ~ e.name ~ 'Response',
  base_package ~ '.' ~ e.package ~ '.dto.Update' ~ e.name ~ 'Request',
  base_package ~ '.' ~ e.package ~ '.service.' ~ e.name ~ 'Service',
  'io.swagger.v3.oas.annotations.Operation',
  'io.swagger.v3.oas.annotations.tags.Tag',
  'jakarta.validation.Valid',
  'jakarta.validation.constraints.Max',
  'jakarta.validation.constraints.Min',
  'java.net.URI',
  'java.util.UUID',
  'lombok.RequiredArgsConstructor',
  'org.springframework.http.ResponseEntity',
  'org.springframework.validation.annotation.Validated',
  'org.springframework.web.bind.annotation.DeleteMapping',
  'org.springframework.web.bind.annotation.GetMapping',
  'org.springframework.web.bind.annotation.PathVariable',
  'org.springframework.web.bind.annotation.PostMapping',
  'org.springframework.web.bind.annotation.PutMapping',
  'org.springframework.web.bind.annotation.RequestBody',
  'org.springframework.web.bind.annotation.RequestMapping',
  'org.springframework.web.bind.annotation.RequestParam',
  'org.springframework.web.bind.annotation.RestController',
  'org.springframework.web.servlet.support.ServletUriComponentsBuilder'] -%}
package {{ base_package }}.{{ e.package }}.controller;

{% for i in imps | sort(case_sensitive=true) -%}
import {{ i }};
{% endfor %}
/**
 * REST entry point for the {@code {{ e.name }}} resource.
 *
 * <p>Serves {@code /api/v1/{{ e.plural_path }}}; owns HTTP concerns only.
 *
 * <p>Delegates all business logic to {@link {{ e.name }}Service}.
 */
@RestController
@RequestMapping("/api/v1/{{ e.plural_path }}")
@RequiredArgsConstructor
@Tag(name = "{{ plural }}")
@Validated
public class {{ e.name }}Controller {

  private final {{ e.name }}Service service;

  /**
   * {@code GET /api/v1/{{ e.plural_path }}} - lists non-deleted {{ e.var_name }} rows as a page.
   *
   * @param page page number, zero-based (default {@code 0})
   * @param size page size, 1-100 inclusive (default {@code 20})
   * @param sortBy entity property to sort by (default {@code createdAt})
   * @param sortDirection {@code ASC} or {@code DESC} (default {@code DESC})
   * @return {@code 200 OK} with the requested page wrapped in {@link ApiResponse}
   */
  @GetMapping
  @Operation(summary = "List {{ plural | lower }}")
  public ResponseEntity<ApiResponse<PageResponse<{{ e.name }}Response>>> findAll(
      @RequestParam(defaultValue = "0") @Min(0) int page,
      @RequestParam(defaultValue = "20") @Min(1) @Max(100) int size,
      @RequestParam(defaultValue = "createdAt") String sortBy,
      @RequestParam(defaultValue = "DESC") String sortDirection) {
{{ assign(4, 'PageResponse<' ~ e.name ~ 'Response> result', 'service.findAll(page, size, sortBy, sortDirection)') }}
{{ wrap(4, 'return ResponseEntity.ok(', ['ApiResponse.success("' ~ plural ~ ' retrieved successfully", result)'], ');') }}
  }

  /**
   * {@code GET /api/v1/{{ e.plural_path }}/{id}} - fetches a single {{ e.var_name }} by id.
   *
   * @param id the {{ e.var_name }} id
   * @return {@code 200 OK} with the {{ e.var_name }}, or {@code 404} when it does not exist
   */
  @GetMapping("/{id}")
  @Operation(summary = "Get {{ e.var_name }} by id")
{{ wrap(2, 'public ResponseEntity<ApiResponse<' ~ e.name ~ 'Response>> findById(', ['@PathVariable UUID id'], ') {') }}
{{ wrap(4, 'return ResponseEntity.ok(', ['ApiResponse.success("' ~ e.name ~ ' retrieved successfully", service.findById(id))'], ');') }}
  }

  /**
   * {@code POST /api/v1/{{ e.plural_path }}} - creates a new {{ e.var_name }}.
   *
   * @param request validated creation payload
   * @return {@code 201 Created} with a {@code Location} header and the created {{ e.var_name }}
   */
  @PostMapping
  @Operation(summary = "Create {{ e.var_name }}")
{{ wrap(2, 'public ResponseEntity<ApiResponse<' ~ e.name ~ 'Response>> create(', ['@Valid @RequestBody Create' ~ e.name ~ 'Request request'], ') {') }}
{{ assign(4, e.name ~ 'Response created', 'service.create(request)') }}
    URI location =
        ServletUriComponentsBuilder.fromCurrentRequest()
            .path("/{id}")
            .buildAndExpand(created.getId())
            .toUri();
    return ResponseEntity.created(location)
        .body(ApiResponse.success("{{ e.name }} created successfully", created));
  }

  /**
   * {@code PUT /api/v1/{{ e.plural_path }}/{id}} - updates an existing {{ e.var_name }}.
   *
   * @param id the {{ e.var_name }} id
   * @param request validated update payload
   * @return {@code 200 OK} with the updated {{ e.var_name }}, or {@code 404} when it does not exist
   */
  @PutMapping("/{id}")
  @Operation(summary = "Update {{ e.var_name }}")
{{ wrap(2, 'public ResponseEntity<ApiResponse<' ~ e.name ~ 'Response>> update(', ['@PathVariable UUID id', '@Valid @RequestBody Update' ~ e.name ~ 'Request request'], ') {') }}
{{ wrap(4, 'return ResponseEntity.ok(', ['ApiResponse.success("' ~ e.name ~ ' updated successfully", service.update(id, request))'], ');') }}
  }

  /**
   * {@code DELETE /api/v1/{{ e.plural_path }}/{id}} - soft-deletes a {{ e.var_name }}.
   *
   * @param id the {{ e.var_name }} id
   * @return {@code 204 No Content}, or {@code 404} when the {{ e.var_name }} does not exist
   */
  @DeleteMapping("/{id}")
  @Operation(summary = "Delete {{ e.var_name }}")
  public ResponseEntity<Void> delete(@PathVariable UUID id) {
    service.delete(id);
    return ResponseEntity.noContent().build();
  }
}
