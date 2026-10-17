{%- set e = entity -%}
{%- set to_one = e.owning_relations | rejectattr('is_collection') | list -%}
{%- set many = e.owning_relations | selectattr('is_collection') | list -%}
{%- set indexed = e.owning_relations | selectattr('index_name') | list -%}
{%- set cascading = e.inverse_relations | selectattr('cascade') | list -%}
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
{#- Java source of a field's default value (the SQL literal is the single source of truth). -#}
{%- macro java_default(f) -%}
{%- set raw = f.default_sql -%}
{%- set inner = raw[1:-1] | replace("''", "'") | replace('\\', '\\\\') | replace('"', '\\"') -%}
{%- if f.type == 'string' -%}"{{ inner }}"
{%- elif f.type == 'long' -%}{{ raw }}L
{%- elif f.type == 'decimal' -%}new BigDecimal("{{ raw }}")
{%- elif f.type == 'boolean' -%}{{ raw | lower }}
{%- elif f.type == 'date' -%}LocalDate.parse("{{ inner }}")
{%- elif f.type == 'instant' -%}Instant.parse("{{ inner }}")
{%- elif f.type == 'uuid' -%}UUID.fromString("{{ inner }}")
{%- elif f.type == 'enum' -%}{{ f.enum_class }}.{{ inner }}
{%- else -%}{{ raw }}
{%- endif -%}
{%- endmacro -%}
{%- set imps = [
  base_package ~ '.common.entity.BaseEntity',
  'jakarta.persistence.Entity',
  'jakarta.persistence.Table',
  'lombok.Builder',
  'lombok.Getter',
  'lombok.NoArgsConstructor',
  'lombok.Setter'] + (e.imports | list) -%}
{#- with no members the all-args constructor would clash with the no-args one -#}
{%- set has_members = e.fields or e.owning_relations or e.inverse_relations -%}
{%- if has_members %}{% set _ = imps.append('lombok.AllArgsConstructor') %}{% endif -%}
{%- if e.fields %}{% set _ = imps.append('jakarta.persistence.Column') %}{% endif -%}
{%- if indexed %}{% set _ = imps.append('jakarta.persistence.Index') %}{% endif -%}
{%- if e.enums %}{% set _ = imps.extend(['jakarta.persistence.EnumType', 'jakarta.persistence.Enumerated']) %}{% endif -%}
{%- if e.owning_relations %}{% set _ = imps.append('jakarta.persistence.FetchType') %}{% endif -%}
{%- if to_one %}{% set _ = imps.append('jakarta.persistence.JoinColumn') %}{% endif -%}
{%- if many %}{% set _ = imps.extend(['jakarta.persistence.JoinColumn', 'jakarta.persistence.JoinTable', 'jakarta.persistence.ManyToMany']) %}{% endif -%}
{%- if e.inverse_relations %}{% set _ = imps.extend(['jakarta.persistence.FetchType', 'jakarta.persistence.OneToMany']) %}{% endif -%}
{%- if cascading %}{% set _ = imps.append('jakarta.persistence.CascadeType') %}{% endif -%}
{%- for r in e.owning_relations -%}
{%- if r.kind == 'many-to-one' %}{% set _ = imps.append('jakarta.persistence.ManyToOne') %}{% endif -%}
{%- if r.kind == 'one-to-one' %}{% set _ = imps.append('jakarta.persistence.OneToOne') %}{% endif -%}
{%- if r.target_package != e.package %}{% set _ = imps.append(base_package ~ '.' ~ r.target_package ~ '.entity.' ~ r.target) %}{% endif -%}
{%- endfor -%}
{%- for i in e.inverse_relations -%}
{%- if i.target_package != e.package %}{% set _ = imps.append(base_package ~ '.' ~ i.target_package ~ '.entity.' ~ i.target) %}{% endif -%}
{%- endfor -%}
package {{ base_package }}.{{ e.package }}.entity;

{% for i in imps | unique(case_sensitive=true) | sort(case_sensitive=true) -%}
import {{ i }};
{% endfor %}
/**
 * JPA entity backing the {@code {{ e.table }}} table.
 *
 * <p>Extends {@code BaseEntity} for the id, audit timestamps, version and soft-delete marker.
 */
@Entity
{%- set defs = [] %}
{%- for r in indexed %}{% set _ = defs.append('@Index(name = "' ~ r.index_name ~ '", columnList = "' ~ r.column ~ '")') %}{% endfor %}
{%- set one = '@Table(name = "' ~ e.table ~ '"' ~ ((', indexes = {' ~ (defs | join(', ')) ~ '}') if defs else '') ~ ')' %}
{%- if one | length <= 100 %}
{{ one }}
{%- else %}
@Table(
    name = "{{ e.table }}",
{%- set arr = '    indexes = {' ~ (defs | join(', ')) ~ '})' %}
{%- if arr | length <= 100 %}
{{ arr }}
{%- else %}
    indexes = {
{%- for d in defs %}
      {{ d }}{{ ',' if not loop.last else '' }}
{%- endfor %}
    })
{%- endif %}
{%- endif %}
@Getter
@Setter
@NoArgsConstructor
{%- if has_members %}
@AllArgsConstructor
{%- endif %}
@Builder
public class {{ e.name }} extends BaseEntity {
{%- for f in e.fields %}
{%- set cargs = ['name = "' ~ f.column ~ '"'] %}
{%- if f.required %}{% set _ = cargs.append('nullable = false') %}{% endif %}
{%- if f.is_text %}{% set _ = cargs.append('columnDefinition = "TEXT"') %}{% endif %}
{%- if f.length is not none %}{% set _ = cargs.append('length = ' ~ f.length) %}{% endif %}
{%- if f.type == 'decimal' %}{% set _ = cargs.extend(['precision = ' ~ f.precision, 'scale = ' ~ f.scale]) %}{% endif %}
{%- if f.unique %}{% set _ = cargs.append('unique = true') %}{% endif %}
{{ '' }}
{%- if f.is_enum %}
  @Enumerated(EnumType.STRING)
{%- endif %}
{{ ann('Column', cargs) }}
{%- if f.default_sql is not none %}
  @Builder.Default
  private {{ f.java_type }} {{ f.name }} = {{ java_default(f) }};
{%- else %}
  private {{ f.java_type }} {{ f.name }};
{%- endif %}
{%- endfor %}
{%- for r in to_one %}
{%- set tag = 'OneToOne' if r.kind == 'one-to-one' else 'ManyToOne' %}
{%- set targs = ['fetch = FetchType.LAZY'] %}
{%- if r.required %}{% set _ = targs.append('optional = false') %}{% endif %}
{%- set jargs = ['name = "' ~ r.column ~ '"'] %}
{%- if r.required %}{% set _ = jargs.append('nullable = false') %}{% endif %}
{%- if r.unique %}{% set _ = jargs.append('unique = true') %}{% endif %}
{{ '' }}
{{ ann(tag, targs) }}
{{ ann('JoinColumn', jargs) }}
  private {{ r.target }} {{ r.name }};
{%- endfor %}
{%- for r in many %}
{{ '' }}
{{ ann('ManyToMany', ['fetch = FetchType.LAZY']) }}
{{ ann('JoinTable', ['name = "' ~ r.join_table ~ '"', 'joinColumns = @JoinColumn(name = "' ~ r.join_column ~ '")', 'inverseJoinColumns = @JoinColumn(name = "' ~ r.inverse_join_column ~ '")']) }}
  @Builder.Default
  private Set<{{ r.target }}> {{ r.name }} = new HashSet<>();
{%- endfor %}
{%- for i in e.inverse_relations %}
{%- set oargs = ['mappedBy = "' ~ i.mapped_by ~ '"', 'fetch = FetchType.LAZY'] %}
{%- if i.cascade %}{% set _ = oargs.append('cascade = CascadeType.ALL') %}{% endif %}
{%- if i.orphan_removal %}{% set _ = oargs.append('orphanRemoval = true') %}{% endif %}
{{ '' }}
{{ ann('OneToMany', oargs) }}
  @Builder.Default
  private List<{{ i.target }}> {{ i.name }} = new ArrayList<>();
{%- endfor %}
{%- for i in e.inverse_relations %}

  /**
   * Adds a child and keeps both sides of the relation in sync.
   *
   * @param child the child to add
   */
  public void {{ i.add_helper }}({{ i.target }} child) {
    {{ i.name }}.add(child);
    child.{{ i.mapped_by_setter }}(this);
  }

  /**
   * Removes a child and keeps both sides of the relation in sync.
   *
   * @param child the child to remove
   */
  public void {{ i.remove_helper }}({{ i.target }} child) {
    {{ i.name }}.remove(child);
    child.{{ i.mapped_by_setter }}(null);
  }
{%- endfor %}

  @Override
  public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof {{ e.name }} other)) return false;
    return getId() != null && getId().equals(other.getId());
  }

  @Override
  public int hashCode() {
    return getClass().hashCode();
  }
{%- for en in e.enums %}

  /** Allowed values of the {@code {{ en.field_name }}} field, stored by name. */
  public enum {{ en.class_name }} {
{%- for v in en.values %}
    {{ v }}{{ ',' if not loop.last else '' }}
{%- endfor %}
  }
{%- endfor %}
}
