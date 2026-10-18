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
{%- set line = pad ~ '    ' ~ a ~ (',' if not loop.last else tail) %}
{%- if line | length > 100 and ' -> ' in a %}
{{ pad ~ '    ' ~ a.split(' -> ')[0] ~ ' ->' }}
{{ pad ~ '        ' ~ a.split(' -> ')[1] ~ (',' if not loop.last else tail) }}
{%- else %}
{{ line }}
{%- endif %}
{%- endfor -%}
{%- endif -%}
{%- endmacro -%}
{%- set uniques = e.fields | selectattr('unique') | list -%}
{%- set one_to_ones = e.owning_relations | selectattr('kind', 'equalto', 'one-to-one') | list -%}
{%- set many = e.owning_relations | selectattr('is_collection') | list -%}
{%- set checks_unique = uniques or one_to_ones -%}
{#- distinct related entities, in declaration order; the entity itself is resolved through `repository` -#}
{%- set targets = [] -%}
{%- set seen = [] -%}
{%- for r in e.owning_relations -%}
{%- if r.target not in seen -%}
{%- set _ = seen.append(r.target) -%}
{%- set _ = targets.append(r) -%}
{%- endif -%}
{%- endfor -%}
{%- set imps = [
  base_package ~ '.common.dto.PageResponse',
  base_package ~ '.common.exception.ResourceNotFoundException',
  base_package ~ '.common.util.PaginationUtils',
  base_package ~ '.' ~ e.package ~ '.dto.Create' ~ e.name ~ 'Request',
  base_package ~ '.' ~ e.package ~ '.dto.' ~ e.name ~ 'Filter',
  base_package ~ '.' ~ e.package ~ '.dto.' ~ e.name ~ 'Response',
  base_package ~ '.' ~ e.package ~ '.dto.Update' ~ e.name ~ 'Request',
  base_package ~ '.' ~ e.package ~ '.entity.' ~ e.name,
  base_package ~ '.' ~ e.package ~ '.mapper.' ~ e.name ~ 'Mapper',
  base_package ~ '.' ~ e.package ~ '.repository.' ~ e.name ~ 'Repository',
  'java.util.Optional',
  'java.util.UUID',
  'lombok.RequiredArgsConstructor',
  'lombok.extern.slf4j.Slf4j',
  'org.springframework.data.domain.Page',
  'org.springframework.data.domain.Pageable',
  'org.springframework.stereotype.Service',
  'org.springframework.transaction.annotation.Transactional'] -%}
{%- if checks_unique %}{% set _ = imps.extend([base_package ~ '.common.exception.ConflictException', 'java.util.function.BooleanSupplier']) %}{% endif -%}
{%- if one_to_ones %}{% set _ = imps.append(base_package ~ '.common.entity.BaseEntity') %}{% endif -%}
{%- if many %}{% set _ = imps.extend(['java.util.HashSet', 'java.util.Set', 'java.util.function.Function']) %}{% endif -%}
{%- for r in targets -%}
{%- if r.target != e.name -%}
{%- set _ = imps.extend([base_package ~ '.' ~ r.target_package ~ '.entity.' ~ r.target, base_package ~ '.' ~ r.target_package ~ '.repository.' ~ r.target ~ 'Repository']) -%}
{%- endif -%}
{%- endfor -%}
package {{ base_package }}.{{ e.package }}.service;

{% for i in imps | unique(case_sensitive=true) | sort(case_sensitive=true) -%}
import {{ i }};
{% endfor %}
/**
 * Default implementation of {@link {{ e.name }}Service}.
 *
 * <p>Read-only by default; mutating methods opt in to a writable transaction.
 */
@Service
@RequiredArgsConstructor
@Slf4j
@Transactional(readOnly = true)
public class {{ e.name }}ServiceImpl implements {{ e.name }}Service {

  private static final String RESOURCE = "{{ e.name }}";

  private final {{ e.name }}Repository repository;
  private final {{ e.name }}Mapper mapper;
{%- for r in targets %}
{%- if r.target != e.name %}
  private final {{ r.target }}Repository {{ r.target_var }}Repository;
{%- endif %}
{%- endfor %}

  /** {@inheritDoc} */
  @Override
  @Transactional(readOnly = true)
  public {{ e.name }}Response findById(UUID id) {
    return mapper.toResponse(getActive(id));
  }

  /** {@inheritDoc} */
  @Override
  @Transactional(readOnly = true)
{{ wrap(2, 'public PageResponse<' ~ e.name ~ 'Response> findAll(', ['int page', 'int size', 'String sortBy', 'String sortDirection', e.name ~ 'Filter filter'], ') {') }}
    Pageable pageable = PaginationUtils.createPageable(page, size, sortBy, sortDirection);
{%- set find_all = 'repository.findAll(filter.toSpecification(), pageable);' %}
{%- if ('    Page<' ~ e.name ~ '> result = ' ~ find_all) | length <= 100 %}
    Page<{{ e.name }}> result = {{ find_all }}
{%- else %}
    Page<{{ e.name }}> result =
        {{ find_all }}
{%- endif %}
    return PaginationUtils.toPageResponse(result, result.map(mapper::toResponse).getContent());
  }

  /** {@inheritDoc} */
  @Override
  @Transactional
  public {{ e.name }}Response create(Create{{ e.name }}Request request) {
{%- for f in uniques %}
{{ wrap(4, 'ensureFree(', ['"' ~ f.name ~ '"', 'request.' ~ f.getter ~ '()', 'null', '() -> repository.existsBy' ~ f.getter[3:] ~ 'AndDeletedAtIsNull(request.' ~ f.getter ~ '())'], ');') }}
{%- endfor %}
{%- for r in one_to_ones %}
{{ wrap(4, 'ensureFree(', ['"' ~ r.name ~ '"', 'request.get' ~ r.id_field[:1] | upper ~ r.id_field[1:] ~ '()', 'null', '() -> repository.existsBy' ~ r.getter[3:] ~ 'IdAndDeletedAtIsNull(request.get' ~ r.id_field[:1] | upper ~ r.id_field[1:] ~ '())'], ');') }}
{%- endfor %}
    {{ e.name }} entity = mapper.toEntity(request);
{%- for r in e.owning_relations %}
{%- set getter = 'request.get' ~ (r.id_field[:1] | upper) ~ r.id_field[1:] ~ '()' %}
{%- if r.is_collection %}
{{ wrap(4, 'entity.' ~ r.setter ~ '(', ['resolveAll(' ~ getter ~ ', this::resolve' ~ r.target ~ ')'], ');') }}
{%- else %}
{{ wrap(4, 'entity.' ~ r.setter ~ '(', ['resolve' ~ r.target ~ '(' ~ getter ~ ')'], ');') }}
{%- endif %}
{%- endfor %}
    {{ e.name }} saved = repository.save(entity);
    log.info("{{ e.name }} created with id: {}", saved.getId());
    return mapper.toResponse(saved);
  }

  /** {@inheritDoc} */
  @Override
  @Transactional
  public {{ e.name }}Response update(UUID id, Update{{ e.name }}Request request) {
    {{ e.name }} entity = getActive(id);
{%- for f in uniques %}
{{ wrap(4, 'ensureFree(', ['"' ~ f.name ~ '"', 'request.' ~ f.getter ~ '()', 'entity.' ~ f.getter ~ '()', '() -> repository.existsBy' ~ f.getter[3:] ~ 'AndDeletedAtIsNull(request.' ~ f.getter ~ '())'], ');') }}
{%- endfor %}
{%- for r in one_to_ones %}
{{ wrap(4, 'ensureFree(', ['"' ~ r.name ~ '"', 'request.get' ~ r.id_field[:1] | upper ~ r.id_field[1:] ~ '()', 'idOf(entity.' ~ r.getter ~ '())', '() -> repository.existsBy' ~ r.getter[3:] ~ 'IdAndDeletedAtIsNull(request.get' ~ r.id_field[:1] | upper ~ r.id_field[1:] ~ '())'], ');') }}
{%- endfor %}
    mapper.updateEntityFromRequest(request, entity);
{%- for r in e.owning_relations %}
{%- set getter = 'request.get' ~ (r.id_field[:1] | upper) ~ r.id_field[1:] ~ '()' %}
{%- if r.is_collection %}
{{ wrap(4, 'entity.' ~ r.setter ~ '(', ['resolveAll(' ~ getter ~ ', this::resolve' ~ r.target ~ ')'], ');') }}
{%- else %}
{{ wrap(4, 'entity.' ~ r.setter ~ '(', ['resolve' ~ r.target ~ '(' ~ getter ~ ')'], ');') }}
{%- endif %}
{%- endfor %}
    {{ e.name }} saved = repository.save(entity);
    log.info("{{ e.name }} updated: {}", id);
    return mapper.toResponse(saved);
  }

  /** {@inheritDoc} */
  @Override
  @Transactional
  public void delete(UUID id) {
    {{ e.name }} entity = getActive(id);
    entity.softDelete();
    repository.save(entity);
    log.info("{{ e.name }} deleted: {}", id);
  }

  private {{ e.name }} getActive(UUID id) {
    return found(repository.findByIdAndDeletedAtIsNull(id), RESOURCE, id);
  }
{%- for r in targets %}

  private {{ r.target }} resolve{{ r.target }}(UUID id) {
{%- if e.owning_relations | selectattr('target', 'equalto', r.target) | rejectattr('required') | rejectattr('is_collection') | list %}
    if (id == null) {
      return null;
    }
{%- endif %}
{{ wrap(4, 'return found(', [('repository' if r.target == e.name else r.target_var ~ 'Repository') ~ '.findByIdAndDeletedAtIsNull(id)', '"' ~ r.target ~ '"', 'id'], ');') }}
  }
{%- endfor %}
{%- if many %}

  private static <T> Set<T> resolveAll(Set<UUID> ids, Function<UUID, T> resolver) {
    Set<T> result = new HashSet<>();
    if (ids != null) {
      ids.forEach(id -> result.add(resolver.apply(id)));
    }
    return result;
  }
{%- endif %}

  private static <T> T found(Optional<T> value, String type, UUID id) {
    return value.orElseThrow(
        () -> new ResourceNotFoundException(type + " not found with id: " + id));
  }
{%- if checks_unique %}

  private static void ensureFree(String field, Object value, Object old, BooleanSupplier taken) {
    if (value != null && !value.equals(old) && taken.getAsBoolean()) {
      throw new ConflictException(RESOURCE + " with " + field + " '" + value + "' already exists");
    }
  }
{%- endif %}
{%- if one_to_ones %}

  private static UUID idOf(BaseEntity entity) {
    return entity == null ? null : entity.getId();
  }
{%- endif %}
}
