{%- set e = entity -%}
{%- set uniques = e.fields | selectattr('unique') | list -%}
{%- set one_to_ones = e.owning_relations | selectattr('kind', 'equalto', 'one-to-one') | list -%}
{%- set checks_unique = uniques or one_to_ones -%}
{%- set to_one = e.owning_relations | rejectattr('is_collection') | list -%}
{%- set many = e.owning_relations | selectattr('is_collection') | list -%}
{%- set optional_relations = e.owning_relations | rejectattr('required') | list -%}
{%- set self_ref = e.owning_relations | selectattr('target', 'equalto', e.name) | list -%}
{#- `when(call).thenReturn(ret);`, broken before `.thenReturn` when it does not fit in 100 columns. -#}
{%- macro stub(call, ret) -%}
{%- set one = '    when(' ~ call ~ ').thenReturn(' ~ ret ~ ');' -%}
{%- if one | length <= 100 -%}
{{ one }}
{%- else -%}
{{ '    when(' ~ call ~ ')' }}
{{ '        .thenReturn(' ~ ret ~ ');' }}
{%- endif -%}
{%- endmacro -%}
{#- distinct related entities, in declaration order -#}
{%- set targets = [] -%}
{%- set seen = [] -%}
{%- for r in e.owning_relations -%}
{%- if r.target not in seen -%}
{%- set _ = seen.append(r.target) -%}
{%- set _ = targets.append(r) -%}
{%- endif -%}
{%- endfor -%}
{%- set imps = [
  base_package ~ '.common.exception.ResourceNotFoundException',
  base_package ~ '.' ~ e.package ~ '.dto.Create' ~ e.name ~ 'Request',
  base_package ~ '.' ~ e.package ~ '.dto.' ~ e.name ~ 'Response',
  base_package ~ '.' ~ e.package ~ '.dto.Update' ~ e.name ~ 'Request',
  base_package ~ '.' ~ e.package ~ '.entity.' ~ e.name,
  base_package ~ '.' ~ e.package ~ '.mapper.' ~ e.name ~ 'Mapper',
  base_package ~ '.' ~ e.package ~ '.repository.' ~ e.name ~ 'Repository',
  'java.util.List',
  'java.util.Optional',
  'java.util.UUID',
  'org.junit.jupiter.api.Test',
  'org.junit.jupiter.api.extension.ExtendWith',
  'org.mockito.InjectMocks',
  'org.mockito.Mock',
  'org.mockito.junit.jupiter.MockitoExtension',
  'org.springframework.data.domain.PageImpl',
  'org.springframework.data.domain.PageRequest',
  'org.springframework.data.domain.Pageable'] -%}
{%- if checks_unique %}{% set _ = imps.append(base_package ~ '.common.exception.ConflictException') %}{% endif -%}
{%- if many %}{% set _ = imps.append('java.util.Set') %}{% endif -%}
{%- for f in e.fields -%}
{%- for i in f.imports %}{% set _ = imps.append(i) %}{% endfor -%}
{%- if f.is_enum %}{% set _ = imps.append(base_package ~ '.' ~ f.enum_import_suffix) %}{% endif -%}
{%- endfor -%}
{%- for r in targets -%}
{%- if r.target != e.name -%}
{%- set _ = imps.extend([base_package ~ '.' ~ r.target_package ~ '.entity.' ~ r.target, base_package ~ '.' ~ r.target_package ~ '.repository.' ~ r.target ~ 'Repository']) -%}
{%- endif -%}
{%- endfor -%}
{#- statements filling every scalar field with a sample value -#}
{%- macro fill(obj, alt) -%}
{%- for f in e.fields %}
    {{ obj }}.{{ f.setter }}({{ f.sample_value_alt if alt else f.sample_value }});
{%- endfor %}
{%- endmacro -%}
{#- statements filling the relation ids of a request -#}
{%- macro fill_ids(obj) -%}
{%- for r in e.owning_relations %}
    {{ obj }}.set{{ r.id_field[:1] | upper }}{{ r.id_field[1:] }}({{ r.id_field }});
{%- endfor %}
{%- endmacro -%}
{#- stubs the related-entity lookups that create/update perform: one `any()` stub per distinct repository, so
    strict stubbing never sees a lookup with arguments it was not stubbed for. A self-reference goes through the
    entity's own repository; update tests cover it with their `any()` stub of the entity lookup instead. -#}
{%- macro stub_relations(required_only=false, include_self=true) -%}
{%- set done = [] -%}
{%- for r in e.owning_relations if r.required or not required_only %}
{%- if r.target not in done and (r.target != e.name or include_self) %}
{%- set _ = done.append(r.target) %}
{{ stub(('repository' if r.target == e.name else r.target_var ~ 'Repository') ~ '.findByIdAndDeletedAtIsNull(any())', 'Optional.of(new ' ~ r.target ~ '())') }}
{%- endif %}
{%- endfor %}
{%- endmacro -%}
package {{ base_package }}.{{ e.package }}.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

{% for i in imps | unique(case_sensitive=true) | sort(case_sensitive=true) -%}
import {{ i }};
{% endfor %}
@ExtendWith(MockitoExtension.class)
class {{ e.name }}ServiceImplTest {

  @Mock private {{ e.name }}Repository repository;

  @Mock private {{ e.name }}Mapper mapper;
{%- for r in targets %}
{%- if r.target != e.name %}

  @Mock private {{ r.target }}Repository {{ r.target_var }}Repository;
{%- endif %}
{%- endfor %}

  @InjectMocks private {{ e.name }}ServiceImpl service;
{%- for r in e.owning_relations %}
{%- if r.is_collection %}

  private final Set<UUID> {{ r.id_field }} = Set.of(UUID.randomUUID());
{%- else %}

  private final UUID {{ r.id_field }} = UUID.randomUUID();
{%- endif %}
{%- endfor %}

  @Test
  void findById_whenFound_returnsResponse() {
    UUID id = UUID.randomUUID();
    {{ e.name }} entity = new {{ e.name }}();
    {{ e.name }}Response response = new {{ e.name }}Response();
    when(repository.findByIdAndDeletedAtIsNull(id)).thenReturn(Optional.of(entity));
    when(mapper.toResponse(entity)).thenReturn(response);

    {{ e.name }}Response result = service.findById(id);

    assertThat(result).isSameAs(response);
  }

  @Test
  void findById_whenNotFound_throwsResourceNotFoundException() {
    UUID id = UUID.randomUUID();
    when(repository.findByIdAndDeletedAtIsNull(id)).thenReturn(Optional.empty());

    assertThrows(ResourceNotFoundException.class, () -> service.findById(id));
  }

  @Test
  void findAll_returnsMappedPage() {
    {{ e.name }} entity = new {{ e.name }}();
    Pageable pageable = PageRequest.of(0, 20);
    when(repository.findAllByDeletedAtIsNull(any()))
        .thenReturn(new PageImpl<>(List.of(entity), pageable, 1));
    when(mapper.toResponse(entity)).thenReturn(new {{ e.name }}Response());

    var result = service.findAll(0, 20, "createdAt", "DESC");

    assertThat(result.getData()).hasSize(1);
    verify(repository).findAllByDeletedAtIsNull(any());
  }

  @Test
  void create_whenValid_resolvesRelationsSavesAndReturnsResponse() {
    Create{{ e.name }}Request request = createRequest();
    {{ e.name }} toSave = new {{ e.name }}();
    {{ e.name }} saved = new {{ e.name }}();
    {{ e.name }}Response response = new {{ e.name }}Response();
    when(mapper.toEntity(request)).thenReturn(toSave);
{{- stub_relations() }}
    when(repository.save(toSave)).thenReturn(saved);
    when(mapper.toResponse(saved)).thenReturn(response);

    {{ e.name }}Response result = service.create(request);

    assertThat(result).isSameAs(response);
{%- for r in e.owning_relations %}
{%- if r.is_collection %}
    assertThat(toSave.{{ r.getter }}()).hasSize(1);
{%- else %}
    assertThat(toSave.{{ r.getter }}()).isNotNull();
{%- endif %}
{%- endfor %}
    verify(repository).save(toSave);
  }
{%- for f in uniques %}

  @Test
  void create_when{{ f.getter[3:] }}IsTaken_throwsConflictException() {
    Create{{ e.name }}Request request = createRequest();
{{ stub('repository.existsBy' ~ f.getter[3:] ~ 'AndDeletedAtIsNull(request.' ~ f.getter ~ '())', 'true') }}

    assertThrows(ConflictException.class, () -> service.create(request));
    verify(repository, never()).save(any());
  }
{%- endfor %}
{%- for r in one_to_ones %}

  @Test
  void create_when{{ r.getter[3:] }}IsTaken_throwsConflictException() {
    Create{{ e.name }}Request request = createRequest();
{{ stub('repository.existsBy' ~ r.getter[3:] ~ 'IdAndDeletedAtIsNull(' ~ r.id_field ~ ')', 'true') }}

    assertThrows(ConflictException.class, () -> service.create(request));
    verify(repository, never()).save(any());
  }
{%- endfor %}
{%- if optional_relations %}

  @Test
  void create_withoutOptionalRelationIds_skipsTheirLookups() {
    Create{{ e.name }}Request request = createRequest();
{%- for r in optional_relations %}
    request.set{{ r.id_field[:1] | upper }}{{ r.id_field[1:] }}(null);
{%- endfor %}
    {{ e.name }} toSave = new {{ e.name }}();
    when(mapper.toEntity(request)).thenReturn(toSave);
{{- stub_relations(true) }}
    when(repository.save(toSave)).thenReturn(toSave);
    when(mapper.toResponse(toSave)).thenReturn(new {{ e.name }}Response());

    service.create(request);

{%- for r in optional_relations %}
{%- if r.is_collection %}
    assertThat(toSave.{{ r.getter }}()).isEmpty();
{%- else %}
    assertThat(toSave.{{ r.getter }}()).isNull();
{%- endif %}
{%- endfor %}
  }
{%- endif %}
{%- for r in e.owning_relations[:1] %}

  @Test
  void create_when{{ r.getter[3:] }}DoesNotExist_throwsResourceNotFoundException() {
    Create{{ e.name }}Request request = createRequest();
    when(mapper.toEntity(request)).thenReturn(new {{ e.name }}());

    assertThrows(ResourceNotFoundException.class, () -> service.create(request));
    verify(repository, never()).save(any());
  }
{%- endfor %}

  @Test
  void update_whenFound_appliesMapperResolvesRelationsAndSaves() {
    UUID id = UUID.randomUUID();
    {{ e.name }} entity = new {{ e.name }}();
    Update{{ e.name }}Request request = updateRequest();
    when(repository.findByIdAndDeletedAtIsNull({{ 'any()' if self_ref else 'id' }})).thenReturn(Optional.of(entity));
{{- stub_relations(false, false) }}
    when(repository.save(entity)).thenReturn(entity);
    when(mapper.toResponse(entity)).thenReturn(new {{ e.name }}Response());

    service.update(id, request);

    verify(mapper).updateEntityFromRequest(request, entity);
    verify(repository).save(entity);
{%- for r in e.owning_relations %}
{%- if r.is_collection %}
    assertThat(entity.{{ r.getter }}()).hasSize(1);
{%- else %}
    assertThat(entity.{{ r.getter }}()).isNotNull();
{%- endif %}
{%- endfor %}
  }
{%- for f in uniques[:1] %}

  @Test
  void update_when{{ f.getter[3:] }}IsUnchanged_doesNotCheckForConflicts() {
    UUID id = UUID.randomUUID();
    {{ e.name }} entity = new {{ e.name }}();
    Update{{ e.name }}Request request = updateRequest();
    entity.{{ f.setter }}(request.{{ f.getter }}());
    when(repository.findByIdAndDeletedAtIsNull({{ 'any()' if self_ref else 'id' }})).thenReturn(Optional.of(entity));
{{- stub_relations(false, false) }}
    when(repository.save(entity)).thenReturn(entity);
    when(mapper.toResponse(entity)).thenReturn(new {{ e.name }}Response());

    service.update(id, request);

    verify(repository, never()).existsBy{{ f.getter[3:] }}AndDeletedAtIsNull(any());
  }
{%- endfor %}
{%- for f in uniques %}

  @Test
  void update_when{{ f.getter[3:] }}ChangesToATakenValue_throwsConflictException() {
    UUID id = UUID.randomUUID();
    {{ e.name }} entity = new {{ e.name }}();
    Update{{ e.name }}Request request = updateRequest();
    when(repository.findByIdAndDeletedAtIsNull(id)).thenReturn(Optional.of(entity));
{{ stub('repository.existsBy' ~ f.getter[3:] ~ 'AndDeletedAtIsNull(request.' ~ f.getter ~ '())', 'true') }}

    assertThrows(ConflictException.class, () -> service.update(id, request));
    verify(repository, never()).save(any());
  }
{%- endfor %}
{%- for r in one_to_ones %}

  @Test
  void update_when{{ r.getter[3:] }}IsTaken_throwsConflictException() {
    UUID id = UUID.randomUUID();
    {{ e.name }} entity = new {{ e.name }}();
    Update{{ e.name }}Request request = updateRequest();
    when(repository.findByIdAndDeletedAtIsNull(id)).thenReturn(Optional.of(entity));
{{ stub('repository.existsBy' ~ r.getter[3:] ~ 'IdAndDeletedAtIsNull(' ~ r.id_field ~ ')', 'true') }}

    assertThrows(ConflictException.class, () -> service.update(id, request));
    verify(repository, never()).save(any());
  }
{%- endfor %}

  @Test
  void update_whenNotFound_throwsResourceNotFoundException() {
    UUID id = UUID.randomUUID();
    Update{{ e.name }}Request request = updateRequest();
    when(repository.findByIdAndDeletedAtIsNull(id)).thenReturn(Optional.empty());

    assertThrows(ResourceNotFoundException.class, () -> service.update(id, request));
    verify(repository, never()).save(any());
  }

  @Test
  void delete_whenFound_softDeletesAndSaves() {
    UUID id = UUID.randomUUID();
    {{ e.name }} entity = new {{ e.name }}();
    when(repository.findByIdAndDeletedAtIsNull(id)).thenReturn(Optional.of(entity));

    service.delete(id);

    assertThat(entity.isDeleted()).isTrue();
    verify(repository).save(entity);
  }

  @Test
  void delete_whenNotFound_throwsResourceNotFoundException() {
    UUID id = UUID.randomUUID();
    when(repository.findByIdAndDeletedAtIsNull(id)).thenReturn(Optional.empty());

    assertThrows(ResourceNotFoundException.class, () -> service.delete(id));
    verify(repository, never()).save(any());
  }

  private Create{{ e.name }}Request createRequest() {
    Create{{ e.name }}Request request = new Create{{ e.name }}Request();
{{- fill('request', false) }}
{{- fill_ids('request') }}
    return request;
  }

  private Update{{ e.name }}Request updateRequest() {
    Update{{ e.name }}Request request = new Update{{ e.name }}Request();
{{- fill('request', true) }}
{{- fill_ids('request') }}
    return request;
  }
}
