{%- set e = entity -%}
{%- set imps = [
  'java.util.UUID',
  'org.junit.jupiter.api.Test'] -%}
{%- for i in e.inverse_relations -%}
{%- if i.target_package != e.package %}{% set _ = imps.append(base_package ~ '.' ~ i.target_package ~ '.entity.' ~ i.target) %}{% endif -%}
{%- endfor -%}
package {{ base_package }}.{{ e.package }}.entity;

import static org.assertj.core.api.Assertions.assertThat;

{% for i in imps | unique(case_sensitive=true) | sort(case_sensitive=true) -%}
import {{ i }};
{% endfor %}
class {{ e.name }}Test {

  @Test
  void equalsAndHashCode_areBasedOnTheId() {
    {{ e.name }} first = new {{ e.name }}();
    {{ e.name }} second = new {{ e.name }}();
    assertThat(first).isNotEqualTo(second);

    UUID id = UUID.randomUUID();
    first.setId(id);
    second.setId(id);

    assertThat(first).isEqualTo(first).isEqualTo(second).hasSameHashCodeAs(second);
    assertThat(first).isNotEqualTo("not an entity");
  }

  @Test
  void builder_startsWithEmptyCollectionsAndNoId() {
    {{ e.name }} entity = {{ e.name }}.builder().build();

    assertThat(entity.getId()).isNull();
    assertThat(entity.isDeleted()).isFalse();
{%- for r in e.owning_relations if r.is_collection %}
    assertThat(entity.{{ r.getter }}()).isEmpty();
{%- endfor %}
{%- for i in e.inverse_relations %}
    assertThat(entity.{{ i.getter }}()).isEmpty();
{%- endfor %}
  }
{%- for i in e.inverse_relations %}

  @Test
  void {{ i.add_helper }}_and_{{ i.remove_helper }}_keepBothSidesInSync() {
    {{ e.name }} parent = new {{ e.name }}();
    {{ i.target }} child = new {{ i.target }}();

    parent.{{ i.add_helper }}(child);

    assertThat(parent.{{ i.getter }}()).containsExactly(child);
    assertThat(child.get{{ i.mapped_by_setter[3:] }}()).isSameAs(parent);

    parent.{{ i.remove_helper }}(child);

    assertThat(parent.{{ i.getter }}()).isEmpty();
    assertThat(child.get{{ i.mapped_by_setter[3:] }}()).isNull();
  }
{%- endfor %}
}
