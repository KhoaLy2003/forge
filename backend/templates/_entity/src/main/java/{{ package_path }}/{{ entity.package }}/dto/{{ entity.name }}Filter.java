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
{%- set imps = [
  base_package ~ '.common.search.SearchSpecifications',
  base_package ~ '.' ~ e.package ~ '.entity.' ~ e.name,
  'lombok.Builder',
  'org.springframework.data.jpa.domain.Specification'] -%}
{%- for p in e.filters -%}
{%- for i in p.imports %}{% set _ = imps.append(i) %}{% endfor -%}
{%- if p.import_suffix %}{% set _ = imps.append(base_package ~ '.' ~ p.import_suffix) %}{% endif -%}
{%- if p.annotation_import %}{% set _ = imps.append(p.annotation_import) %}{% endif -%}
{%- endfor -%}
{%- set components = [] -%}
{%- set predicates = [] -%}
{%- for p in e.filters -%}
{%- set _ = components.append((p.annotation ~ ' ' if p.annotation else '') ~ p.java_type ~ ' ' ~ p.name) -%}
{%- set _ = predicates.append('SearchSpecifications.' ~ p.op ~ '("' ~ p.attribute ~ '", ' ~ p.name ~ ')') -%}
{%- endfor -%}
package {{ base_package }}.{{ e.package }}.dto;

{% for i in imps | unique(case_sensitive=true) | sort(case_sensitive=true) -%}
import {{ i }};
{% endfor %}
/**
 * Optional filters for listing {{ e.var_name }} rows.
 *
 * <p>A component left {@code null} is ignored; soft-deleted rows are always excluded.
 */
@Builder
{{ wrap(0, 'public record ' ~ e.name ~ 'Filter(', components, ') {') }}

  /**
   * Turns the supplied filters into a query specification.
   *
   * @return the specification matching every supplied filter and no soft-deleted row
   */
  public Specification<{{ e.name }}> toSpecification() {
{{ wrap(4, 'return SearchSpecifications.notDeletedAnd(', predicates, ');') }}
  }
}
