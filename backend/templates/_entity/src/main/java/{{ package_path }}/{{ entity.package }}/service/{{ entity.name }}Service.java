{%- set e = entity -%}
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
{%- set checks_unique = (e.fields | selectattr('unique') | list) or (e.owning_relations | selectattr('kind', 'equalto', 'one-to-one') | list) -%}
{%- set imps = [
  base_package ~ '.common.dto.PageResponse',
  base_package ~ '.common.exception.ResourceNotFoundException',
  base_package ~ '.' ~ e.package ~ '.dto.Create' ~ e.name ~ 'Request',
  base_package ~ '.' ~ e.package ~ '.dto.' ~ e.name ~ 'Filter',
  base_package ~ '.' ~ e.package ~ '.dto.' ~ e.name ~ 'Response',
  base_package ~ '.' ~ e.package ~ '.dto.Update' ~ e.name ~ 'Request',
  'java.util.UUID'] -%}
{%- if checks_unique %}{% set _ = imps.append(base_package ~ '.common.exception.ConflictException') %}{% endif -%}
package {{ base_package }}.{{ e.package }}.service;

{% for i in imps | unique(case_sensitive=true) | sort(case_sensitive=true) -%}
import {{ i }};
{% endfor %}
/**
 * Business operations for the {@code {{ e.name }}} resource.
 *
 * <p>Implemented by {@link {{ e.name }}ServiceImpl}; controllers depend on this interface only.
 */
public interface {{ e.name }}Service {

  /**
   * Retrieves a single non-deleted {{ e.var_name }} by id.
   *
   * @param id the {{ e.var_name }} id
   * @return the matching {{ e.var_name }}
   * @throws ResourceNotFoundException if no non-deleted {{ e.var_name }} has the given id
   */
  {{ e.name }}Response findById(UUID id);

  /**
   * Retrieves a page of non-deleted {{ e.var_name }} rows.
   *
   * @param page zero-based page number
   * @param size page size
   * @param sortBy property to sort by
   * @param sortDirection {@code ASC} or {@code DESC}
   * @param filter optional field filters; a filter left {@code null} is ignored
   * @return the requested page
   */
{{ wrap(2, 'PageResponse<' ~ e.name ~ 'Response> findAll(', ['int page', 'int size', 'String sortBy', 'String sortDirection', e.name ~ 'Filter filter'], ');') }}

  /**
   * Creates a new {{ e.var_name }}.
   *
   * @param request the validated creation payload
   * @return the created {{ e.var_name }}
{%- if checks_unique %}
   * @throws ConflictException if a unique value is already taken by a non-deleted {{ e.var_name }}
{%- endif %}
{%- if e.owning_relations %}
   * @throws ResourceNotFoundException if a referenced related entity does not exist
{%- endif %}
   */
  {{ e.name }}Response create(Create{{ e.name }}Request request);

  /**
   * Updates an existing {{ e.var_name }}.
   *
   * @param id the {{ e.var_name }} id
   * @param request the validated update payload
   * @return the updated {{ e.var_name }}
{%- if checks_unique %}
   * @throws ConflictException if a changed unique value is already taken
{%- endif %}
   * @throws ResourceNotFoundException if the {{ e.var_name }} or a referenced entity does not exist
   */
  {{ e.name }}Response update(UUID id, Update{{ e.name }}Request request);

  /**
   * Soft-deletes a {{ e.var_name }}: the row is kept with {@code deletedAt} set.
   *
   * @param id the {{ e.var_name }} id
   * @throws ResourceNotFoundException if no non-deleted {{ e.var_name }} has the given id
   */
  void delete(UUID id);
}
