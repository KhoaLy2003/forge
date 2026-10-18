{%- set e = entity -%}
{%- set uniques = e.fields | selectattr('unique') | list -%}
{%- set one_to_ones = e.owning_relations | selectattr('kind', 'equalto', 'one-to-one') | list -%}
{%- set imps = [
  base_package ~ '.' ~ e.package ~ '.entity.' ~ e.name,
  'java.util.Optional',
  'java.util.UUID',
  'org.springframework.data.jpa.repository.JpaRepository',
  'org.springframework.data.jpa.repository.JpaSpecificationExecutor'] -%}
{%- for f in uniques -%}
{%- for i in f.imports %}{% set _ = imps.append(i) %}{% endfor -%}
{%- if f.is_enum %}{% set _ = imps.append(base_package ~ '.' ~ f.enum_import_suffix) %}{% endif -%}
{%- endfor -%}
package {{ base_package }}.{{ e.package }}.repository;

{% for i in imps | unique(case_sensitive=true) | sort(case_sensitive=true) -%}
import {{ i }};
{% endfor %}
/**
 * Spring Data repository for {@link {{ e.name }}}.
 *
 * <p>Every finder carries {@code AndDeletedAtIsNull} so soft-deleted rows stay hidden. Listing goes
 * through {@link JpaSpecificationExecutor} with {@code {{ e.name }}Filter#toSpecification()}, which
 * excludes soft-deleted rows itself.
 */
{% set decl = 'public interface ' ~ e.name ~ 'Repository extends JpaRepository<' ~ e.name ~ ', UUID>, JpaSpecificationExecutor<' ~ e.name ~ '> {' -%}
{%- if decl | length <= 100 -%}
{{ decl }}
{%- else -%}
public interface {{ e.name }}Repository
    extends JpaRepository<{{ e.name }}, UUID>, JpaSpecificationExecutor<{{ e.name }}> {
{%- endif %}

  /**
   * Finds a non-deleted {{ e.var_name }} by id.
   *
   * @param id the {{ e.var_name }} id
   * @return the {{ e.var_name }} if present and not soft-deleted, otherwise empty
   */
  Optional<{{ e.name }}> findByIdAndDeletedAtIsNull(UUID id);
{%- for f in uniques %}

  /**
   * Checks whether a non-deleted {{ e.var_name }} with the given {{ f.name }} exists.
   *
   * @param {{ f.name }} the {{ f.name }} to look for
   * @return {@code true} if one exists
   */
  boolean existsBy{{ f.getter[3:] }}AndDeletedAtIsNull({{ f.java_type }} {{ f.name }});
{%- endfor %}
{%- for r in one_to_ones %}

  /**
   * Checks whether a non-deleted {{ e.var_name }} already points at the given {{ r.name }}.
   *
   * @param {{ r.id_field }} the id of the {{ r.name }} to look for
   * @return {@code true} if one exists
   */
  boolean existsBy{{ r.getter[3:] }}IdAndDeletedAtIsNull(UUID {{ r.id_field }});
{%- endfor %}
}
