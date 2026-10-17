{%- set e = entity -%}
{%- set many = e.owning_relations | selectattr('is_collection') | list -%}
{%- set imps = [
  'java.time.Instant',
  'java.util.UUID',
  'lombok.AllArgsConstructor',
  'lombok.Builder',
  'lombok.Data',
  'lombok.NoArgsConstructor'] -%}
{%- if many %}{% set _ = imps.append('java.util.Set') %}{% endif -%}
{%- for f in e.fields -%}
{%- for i in f.imports %}{% set _ = imps.append(i) %}{% endfor -%}
{%- if f.is_enum %}{% set _ = imps.append(base_package ~ '.' ~ f.enum_import_suffix) %}{% endif -%}
{%- endfor -%}
package {{ base_package }}.{{ e.package }}.dto;

{% for i in imps | unique(case_sensitive=true) | sort(case_sensitive=true) -%}
import {{ i }};
{% endfor %}
/**
 * Outbound payload returned by every {@code {{ e.name }}} endpoint.
 *
 * <p>Exposes audit metadata, the optimistic-locking version and related ids, never nested entities.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class {{ e.name }}Response {

  private UUID id;
{%- for f in e.fields %}
  private {{ f.java_type }} {{ f.name }};
{%- endfor %}
{%- for r in e.owning_relations %}
  private {{ r.id_java_type }} {{ r.id_field }};
{%- endfor %}
  private Instant createdAt;
  private Instant updatedAt;
  private Long version;
}
