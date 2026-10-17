{%- set e = entity -%}
{%- set uniques = e.fields | selectattr('unique') | list -%}
{%- set one_to_ones = e.owning_relations | selectattr('kind', 'equalto', 'one-to-one') | list -%}
{%- set many = e.owning_relations | selectattr('is_collection') | list -%}
{#- Line(s) for `head + arg + tail`: one line, else the argument on a continuation line. -#}
{%- macro wrap(indent, head, arg, tail) -%}
{%- set pad = ' ' * indent -%}
{%- if (pad ~ head ~ arg ~ tail) | length <= 100 -%}
{{ pad ~ head ~ arg ~ tail }}
{%- else -%}
{{ pad ~ head }}
{{ pad ~ '    ' ~ arg ~ tail }}
{%- endif -%}
{%- endmacro -%}
{#- `head.seg.seg;`, one chain segment per line when it does not fit in 100 columns. -#}
{%- macro chain(head, segs) -%}
{%- set one = '    ' ~ head ~ (segs | join('')) ~ ';' -%}
{%- if one | length <= 100 -%}
{{ one }}
{%- else -%}
{{ '    ' ~ head }}
{%- for s in segs %}
{{ '        ' ~ s ~ (';' if loop.last else '') }}
{%- endfor -%}
{%- endif -%}
{%- endmacro -%}
{#- Related entities this test must be able to persist: every target of an owning relation, plus the
    targets of their required relations (the required graph is acyclic). `entities` is in dependency
    order, so walking it backwards visits dependents first. -#}
{%- set need = [] -%}
{%- for r in e.owning_relations -%}
{%- if r.target != e.name and r.target not in need %}{% set _ = need.append(r.target) %}{% endif -%}
{%- endfor -%}
{%- set closure = [] -%}
{%- for ent in entities | reverse -%}
{%- if ent.name in need -%}
{%- set _ = closure.append(ent) -%}
{%- for rr in ent.owning_relations if rr.required and rr.target not in need %}{% set _ = need.append(rr.target) %}{% endfor -%}
{%- endif -%}
{%- endfor -%}
{%- set closure_names = closure | map(attribute='name') | list -%}
{%- set self_relations = e.owning_relations | selectattr('target', 'equalto', e.name) | list -%}
{%- set imps = [
  base_package ~ '.common.config.JpaAuditingConfig',
  base_package ~ '.' ~ e.package ~ '.entity.' ~ e.name,
  'org.junit.jupiter.api.Test',
  'org.springframework.beans.factory.annotation.Autowired',
  'org.springframework.boot.data.jpa.test.autoconfigure.DataJpaTest',
  'org.springframework.boot.jdbc.test.autoconfigure.AutoConfigureTestDatabase',
  'org.springframework.context.annotation.Import',
  'org.springframework.data.domain.Page',
  'org.springframework.data.domain.PageRequest',
  'org.springframework.test.context.DynamicPropertyRegistry',
  'org.springframework.test.context.DynamicPropertySource',
  'org.testcontainers.containers.PostgreSQLContainer',
  'org.testcontainers.junit.jupiter.Container',
  'org.testcontainers.junit.jupiter.Testcontainers'] -%}
{%- for f in e.fields -%}
{%- for i in f.imports %}{% set _ = imps.append(i) %}{% endfor -%}
{%- if f.is_enum %}{% set _ = imps.append(base_package ~ '.' ~ f.enum_import_suffix) %}{% endif -%}
{%- endfor -%}
{%- for ent in closure -%}
{%- set _ = imps.append(base_package ~ '.' ~ ent.package ~ '.entity.' ~ ent.name) -%}
{%- if ent.name != e.name %}{% set _ = imps.append(base_package ~ '.' ~ ent.package ~ '.repository.' ~ ent.name ~ 'Repository') %}{% endif -%}
{%- for f in ent.fields -%}
{%- for i in f.imports %}{% set _ = imps.append(i) %}{% endfor -%}
{%- if f.is_enum %}{% set _ = imps.append(base_package ~ '.' ~ f.enum_import_suffix) %}{% endif -%}
{%- endfor -%}
{%- endfor -%}
package {{ base_package }}.{{ e.package }}.repository;

import static org.assertj.core.api.Assertions.assertThat;

{% for i in imps | unique(case_sensitive=true) | sort(case_sensitive=true) -%}
import {{ i }};
{% endfor %}
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Testcontainers
@Import(JpaAuditingConfig.class)
class {{ e.name }}RepositoryTest {

  @Container
  static final PostgreSQLContainer<?> postgres =
      new PostgreSQLContainer<>("postgres:16-alpine")
          .withDatabaseName("testdb")
          .withUsername("test")
          .withPassword("test");

  @DynamicPropertySource
  static void configureProperties(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", postgres::getJdbcUrl);
    registry.add("spring.datasource.username", postgres::getUsername);
    registry.add("spring.datasource.password", postgres::getPassword);
  }

  @Autowired {{ e.name }}Repository repository;
{%- for ent in closure %}

  @Autowired {{ ent.name }}Repository {{ ent.var_name }}Repository;

  private {{ ent.name }} {{ ent.var_name }};
{%- endfor %}

  @Test
  void findByIdAndDeletedAtIsNull_excludesSoftDeletedRows() {
    {{ e.name }} active = repository.save(newEntity(false));

    {{ e.name }} deleted = newEntity(true);
    deleted.softDelete();
    deleted = repository.save(deleted);

    assertThat(repository.findByIdAndDeletedAtIsNull(active.getId())).isPresent();
    assertThat(repository.findByIdAndDeletedAtIsNull(deleted.getId())).isEmpty();
  }

  @Test
  void findAllByDeletedAtIsNull_returnsOnlyActiveRowsPaged() {
    {{ e.name }} active = repository.save(newEntity(false));
    {{ e.name }} deleted = newEntity(true);
    deleted.softDelete();
    {{ e.name }} savedDeleted = repository.save(deleted);

    Page<{{ e.name }}> page = repository.findAllByDeletedAtIsNull(PageRequest.of(0, 10));

{{ chain('assertThat(page.getContent())', ['.extracting(' ~ e.name ~ '::getId)', '.contains(active.getId())']) }}
{{ chain('assertThat(page.getContent())', ['.extracting(' ~ e.name ~ '::getId)', '.doesNotContain(savedDeleted.getId())']) }}
  }

  @Test
  void save_populatesAuditAndVersionFields() {
    {{ e.name }} saved = repository.save(newEntity(false));

    assertThat(saved.getId()).isNotNull();
    assertThat(saved.getCreatedAt()).isNotNull();
    assertThat(saved.getUpdatedAt()).isNotNull();
    assertThat(saved.getVersion()).isEqualTo(0L);
  }
{%- for f in uniques %}

  @Test
  void existsBy{{ f.getter[3:] }}AndDeletedAtIsNull_ignoresSoftDeletedRows() {
    {{ e.name }} saved = repository.save(newEntity(false));
    {{ f.java_type }} value = saved.{{ f.getter }}();

{{ chain('assertThat(repository.existsBy' ~ f.getter[3:] ~ 'AndDeletedAtIsNull(value))', ['.isTrue()']) }}

    saved.softDelete();
    repository.saveAndFlush(saved);

{{ chain('assertThat(repository.existsBy' ~ f.getter[3:] ~ 'AndDeletedAtIsNull(value))', ['.isFalse()']) }}
  }
{%- endfor %}
{%- for r in one_to_ones %}

  @Test
  void existsBy{{ r.getter[3:] }}IdAndDeletedAtIsNull_ignoresSoftDeletedRows() {
    {{ r.target }} target = saved{{ r.target }}();
    {{ e.name }} entity = newEntity(false);
    entity.{{ r.setter }}(target);
    {{ e.name }} saved = repository.save(entity);

{{ chain('assertThat(repository.existsBy' ~ r.getter[3:] ~ 'IdAndDeletedAtIsNull(target.getId()))', ['.isTrue()']) }}

    saved.softDelete();
    repository.saveAndFlush(saved);

{{ chain('assertThat(repository.existsBy' ~ r.getter[3:] ~ 'IdAndDeletedAtIsNull(target.getId()))', ['.isFalse()']) }}
  }
{%- endfor %}
{%- if e.owning_relations %}

  @Test
  void saveAndFlush_persistsRelations() {
    {{ e.name }} entity = newEntity(false);
{%- if self_relations %}
{%- if e.name in closure_names %}
    {{ e.name }} other = saved{{ e.name }}();
{%- else %}
    {{ e.name }} other = repository.save(newEntity(true));
{%- endif %}
{%- endif %}
{%- for r in e.owning_relations %}
{%- set source = 'other' if r.target == e.name else 'saved' ~ r.target ~ '()' %}
{%- if r.is_collection %}
    entity.{{ r.getter }}().add({{ source }});
{%- elif not r.required %}
    entity.{{ r.setter }}({{ source }});
{%- endif %}
{%- endfor %}

    {{ e.name }} saved = repository.saveAndFlush(entity);

    assertThat(saved.getId()).isNotNull();
  }
{%- endif %}

  private {{ e.name }} newEntity(boolean alt) {
    {{ e.name }} entity = new {{ e.name }}();
{%- for f in e.fields %}
{%- if f.sample_value == f.sample_value_alt %}
    entity.{{ f.setter }}({{ f.sample_value }});
{%- else %}
{{ wrap(4, 'entity.' ~ f.setter ~ '(', 'alt ? ' ~ f.sample_value_alt ~ ' : ' ~ f.sample_value, ');') }}
{%- endif %}
{%- endfor %}
{%- for r in e.owning_relations if r.required %}
    entity.{{ r.setter }}(saved{{ r.target }}());
{%- endfor %}
    return entity;
  }
{%- for ent in closure %}

  private {{ ent.name }} saved{{ ent.name }}() {
    if ({{ ent.var_name }} != null) {
      return {{ ent.var_name }};
    }
    {{ ent.name }} entity = new {{ ent.name }}();
{%- for f in ent.fields %}
    entity.{{ f.setter }}({{ f.sample_value_alt }});
{%- endfor %}
{%- for rr in ent.owning_relations if rr.required %}
    entity.{{ rr.setter }}(saved{{ rr.target }}());
{%- endfor %}
    {{ ent.var_name }} = {{ ent.var_name }}Repository.save(entity);
    return {{ ent.var_name }};
  }
{%- endfor %}
}
