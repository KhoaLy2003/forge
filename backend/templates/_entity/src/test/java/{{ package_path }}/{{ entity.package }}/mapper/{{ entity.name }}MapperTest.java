{%- set e = entity -%}
{%- set many = e.owning_relations | selectattr('is_collection') | list -%}
{%- set to_one = e.owning_relations | rejectattr('is_collection') | list -%}
{%- set imps = [
  base_package ~ '.' ~ e.package ~ '.dto.Create' ~ e.name ~ 'Request',
  base_package ~ '.' ~ e.package ~ '.dto.' ~ e.name ~ 'Response',
  base_package ~ '.' ~ e.package ~ '.dto.Update' ~ e.name ~ 'Request',
  base_package ~ '.' ~ e.package ~ '.entity.' ~ e.name,
  'java.time.Instant',
  'java.util.UUID',
  'org.junit.jupiter.api.Test'] -%}
{%- if many %}{% set _ = imps.append('java.util.Set') %}{% endif -%}
{%- for f in e.fields -%}
{%- for i in f.imports %}{% set _ = imps.append(i) %}{% endfor -%}
{%- if f.is_enum %}{% set _ = imps.append(base_package ~ '.' ~ f.enum_import_suffix) %}{% endif -%}
{%- endfor -%}
{%- for r in e.owning_relations -%}
{%- if r.target != e.name %}{% set _ = imps.append(base_package ~ '.' ~ r.target_package ~ '.entity.' ~ r.target) %}{% endif -%}
{%- endfor -%}
{#- `assertThat(subject).matcher;`, broken before the matcher when it does not fit in 100 columns. -#}
{%- macro check(subject, matcher) -%}
{%- set one = '    assertThat(' ~ subject ~ ').' ~ matcher ~ ';' -%}
{%- if one | length <= 100 -%}
{{ one }}
{%- else -%}
{{ '    assertThat(' ~ subject ~ ')' }}
{{ '        .' ~ matcher ~ ';' }}
{%- endif -%}
{%- endmacro -%}
{#- statements filling every scalar field with a sample value -#}
{%- macro fill(obj, alt) -%}
{%- for f in e.fields %}
    {{ obj }}.{{ f.setter }}({{ f.sample_value_alt if alt else f.sample_value }});
{%- endfor %}
{%- endmacro -%}
{#- assertions that every scalar field was copied from `source` to `target` -#}
{%- macro same_fields(target, source) -%}
{%- for f in e.fields %}
    assertThat({{ target }}.{{ f.getter }}()).isEqualTo({{ source }}.{{ f.getter }}());
{%- endfor %}
{%- endmacro -%}
package {{ base_package }}.{{ e.package }}.mapper;

import static org.assertj.core.api.Assertions.assertThat;

{% for i in imps | unique(case_sensitive=true) | sort(case_sensitive=true) -%}
import {{ i }};
{% endfor %}
class {{ e.name }}MapperTest {

  private final {{ e.name }}Mapper mapper = new {{ e.name }}MapperImpl();

  @Test
  void toEntity_mapsScalarFieldsAndLeavesRelationsToTheService() {
    Create{{ e.name }}Request request = new Create{{ e.name }}Request();
{{- fill('request', false) }}
{%- for r in e.owning_relations %}
{%- if r.is_collection %}
    request.set{{ r.id_field[:1] | upper }}{{ r.id_field[1:] }}(Set.of(UUID.randomUUID()));
{%- else %}
    request.set{{ r.id_field[:1] | upper }}{{ r.id_field[1:] }}(UUID.randomUUID());
{%- endif %}
{%- endfor %}

    {{ e.name }} entity = mapper.toEntity(request);
{{ '' }}
{{- same_fields('entity', 'request') }}
{%- for r in e.owning_relations %}
{%- if r.is_collection %}
    assertThat(entity.{{ r.getter }}()).isEmpty();
{%- else %}
    assertThat(entity.{{ r.getter }}()).isNull();
{%- endif %}
{%- endfor %}
    assertThat(entity.getId()).isNull();
  }
{%- for f in e.fields if f.default_sql is not none %}
{%- if loop.first %}

  @Test
  void toEntity_keepsFieldDefaultsWhenTheRequestOmitsValues() {
    {{ e.name }} entity = mapper.toEntity(new Create{{ e.name }}Request());

{%- endif %}
    assertThat(entity.{{ f.getter }}()).isNotNull();
{%- if loop.last %}
  }
{%- endif %}
{%- endfor %}

  @Test
  void toResponse_mapsFieldsAuditMetadataAndRelationIds() {
    {{ e.name }} entity = new {{ e.name }}();
    UUID id = UUID.randomUUID();
    Instant createdAt = Instant.now().minusSeconds(60);
    Instant updatedAt = Instant.now();
    entity.setId(id);
    entity.setCreatedAt(createdAt);
    entity.setUpdatedAt(updatedAt);
    entity.setVersion(3L);
{{- fill('entity', false) }}
{%- for r in e.owning_relations %}
    {{ r.target }} {{ r.name }}Target = new {{ r.target }}();
    {{ r.name }}Target.setId(UUID.randomUUID());
{%- if r.is_collection %}
    entity.{{ r.setter }}(Set.of({{ r.name }}Target));
{%- else %}
    entity.{{ r.setter }}({{ r.name }}Target);
{%- endif %}
{%- endfor %}

    {{ e.name }}Response response = mapper.toResponse(entity);

    assertThat(response.getId()).isEqualTo(id);
{{- same_fields('response', 'entity') }}
{%- for r in e.owning_relations %}
{%- set ids = 'response.get' ~ (r.id_field[:1] | upper) ~ r.id_field[1:] ~ '()' %}
{%- if r.is_collection %}
{{ check(ids, 'containsExactly(' ~ r.name ~ 'Target.getId())') }}
{%- else %}
{{ check(ids, 'isEqualTo(' ~ r.name ~ 'Target.getId())') }}
{%- endif %}
{%- endfor %}
    assertThat(response.getCreatedAt()).isEqualTo(createdAt);
    assertThat(response.getUpdatedAt()).isEqualTo(updatedAt);
    assertThat(response.getVersion()).isEqualTo(3L);
  }
{%- if e.owning_relations %}

  @Test
  void toResponse_withoutRelations_returnsNoRelationIds() {
    {{ e.name }}Response response = mapper.toResponse(new {{ e.name }}());

{%- for r in e.owning_relations %}
{%- if r.is_collection %}
    assertThat(response.get{{ r.id_field[:1] | upper }}{{ r.id_field[1:] }}()).isEmpty();
{%- else %}
    assertThat(response.get{{ r.id_field[:1] | upper }}{{ r.id_field[1:] }}()).isNull();
{%- endif %}
{%- endfor %}
  }
{%- endif %}

  @Test
  void updateEntityFromRequest_appliesScalarFieldsInPlace() {
    {{ e.name }} entity = new {{ e.name }}();
    Update{{ e.name }}Request request = new Update{{ e.name }}Request();
{{- fill('request', true) }}

    mapper.updateEntityFromRequest(request, entity);
{{ '' }}
{{- same_fields('entity', 'request') }}
    assertThat(entity.getId()).isNull();
  }

  @Test
  void nullInputs_areMappedToNull() {
    assertThat(mapper.toEntity(null)).isNull();
    assertThat(mapper.toResponse(null)).isNull();
    mapper.updateEntityFromRequest(null, new {{ e.name }}());
  }
{%- if many %}

  @Test
  void ids_ofNull_isEmpty() {
    assertThat(mapper.ids(null)).isEmpty();
  }
{%- endif %}
}
