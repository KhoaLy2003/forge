{%- set e = entity -%}
{%- set creating = true -%}
{#- Annotation with arguments: one line when it fits in 100 columns, else one argument per line. -#}
{%- macro ann(name, args) -%}
{%- set one = '  @' ~ name ~ '(' ~ (args | join(', ')) ~ ')' -%}
{%- if one | length <= 100 -%}
{{ one }}
{%- else -%}
{{ '  @' ~ name ~ '(' }}
{%- for a in args %}
{{ '      ' ~ a ~ (',' if not loop.last else ')') }}
{%- endfor -%}
{%- endif -%}
{%- endmacro -%}
{%- set to_one = e.owning_relations | rejectattr('is_collection') | list -%}
{%- set many = e.owning_relations | selectattr('is_collection') | list -%}
{%- set imps = [
  'lombok.Builder',
  'lombok.Data',
  'lombok.NoArgsConstructor'] -%}
{#- with no members the all-args constructor would clash with the no-args one -#}
{%- set has_members = e.fields or e.owning_relations -%}
{%- if has_members %}{% set _ = imps.append('lombok.AllArgsConstructor') %}{% endif -%}
{%- if to_one or many %}{% set _ = imps.append('java.util.UUID') %}{% endif -%}
{%- if many %}{% set _ = imps.append('java.util.Set') %}{% endif -%}
{%- if to_one | selectattr('required') | list %}{% set _ = imps.append('jakarta.validation.constraints.NotNull') %}{% endif -%}
{%- for f in e.fields -%}
{%- for i in f.imports %}{% set _ = imps.append(i) %}{% endfor -%}
{%- if f.is_enum %}{% set _ = imps.append(base_package ~ '.' ~ f.enum_import_suffix) %}{% endif -%}
{%- for a in f.validation -%}
{%- if not (creating and f.default_sql is not none and a in ['@NotNull', '@NotBlank']) %}{% set _ = imps.append('jakarta.validation.constraints.' ~ a.split('(')[0][1:]) %}{% endif -%}
{%- endfor -%}
{%- endfor -%}
package {{ base_package }}.{{ e.package }}.dto;

{% for i in imps | unique(case_sensitive=true) | sort(case_sensitive=true) -%}
import {{ i }};
{% endfor %}
/**
 * Inbound payload for {@code POST /api/v1/{{ e.plural_path }}}.
 *
 * <p>Carries only client-supplied fields and related ids; server-managed fields are never accepted.
 */
@Data
@Builder
@NoArgsConstructor
{%- if has_members %}
@AllArgsConstructor
{%- endif %}
public class Create{{ e.name }}Request {
{%- for f in e.fields %}
{%- set label = f.column | replace('_', ' ') | capitalize %}
{{ '' }}
{%- for a in f.validation %}
{%- if not (creating and f.default_sql is not none and a in ['@NotNull', '@NotBlank']) %}
{%- set aname = a.split('(')[0] %}
{%- if aname in ['@NotNull', '@NotBlank'] %}
{{ ann(aname[1:], ['message = "' ~ label ~ ' is required"']) }}
{%- elif aname == '@Size' %}
{%- set n = a.split('=')[1].rstrip(')').strip() %}
{{ ann('Size', ['max = ' ~ n, 'message = "' ~ label ~ ' must be at most ' ~ n ~ ' characters"']) }}
{%- elif aname == '@Digits' %}
{{ ann('Digits', ['integer = ' ~ (f.precision - f.scale), 'fraction = ' ~ f.scale, 'message = "' ~ label ~ ' must have at most ' ~ (f.precision - f.scale) ~ ' integer and ' ~ f.scale ~ ' fraction digits"']) }}
{%- endif %}
{%- endif %}
{%- endfor %}
  private {{ f.java_type }} {{ f.name }};
{%- endfor %}
{%- for r in e.owning_relations %}
{%- set label = (r.column[:-3] if r.column else r.name) | replace('_', ' ') | capitalize %}
{{ '' }}
{%- if r.required %}
{{ ann('NotNull', ['message = "' ~ label ~ ' is required"']) }}
{%- endif %}
  private {{ r.id_java_type }} {{ r.id_field }};
{%- endfor %}
{%- if has_members %}
}
{%- else %}}
{%- endif %}
