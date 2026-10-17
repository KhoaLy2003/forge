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
{%- set many = e.owning_relations | selectattr('is_collection') | list -%}
{%- set imps = [
  base_package ~ '.' ~ e.package ~ '.dto.Create' ~ e.name ~ 'Request',
  base_package ~ '.' ~ e.package ~ '.dto.' ~ e.name ~ 'Response',
  base_package ~ '.' ~ e.package ~ '.dto.Update' ~ e.name ~ 'Request',
  base_package ~ '.' ~ e.package ~ '.entity.' ~ e.name,
  'org.mapstruct.BeanMapping',
  'org.mapstruct.Mapper',
  'org.mapstruct.Mapping',
  'org.mapstruct.MappingTarget',
  'org.mapstruct.NullValueCheckStrategy',
  'org.mapstruct.ReportingPolicy'] -%}
{%- if many %}{% set _ = imps.extend([base_package ~ '.common.entity.BaseEntity', 'java.util.Collection', 'java.util.Set', 'java.util.UUID', 'java.util.stream.Collectors']) %}{% endif -%}
package {{ base_package }}.{{ e.package }}.mapper;

{% for i in imps | unique(case_sensitive=true) | sort(case_sensitive=true) -%}
import {{ i }};
{% endfor %}
/**
 * MapStruct mapper between {@link {{ e.name }}} and its request and response DTOs.
 *
 * <p>Relations are never mapped here: the service resolves related entities from the ids.
 */
@Mapper(componentModel = "spring", unmappedTargetPolicy = ReportingPolicy.IGNORE)
public interface {{ e.name }}Mapper {

  /**
   * Maps a creation request to a new {@link {{ e.name }}}; null values keep defaults.
   *
   * @param request the validated creation payload
   * @return a new, unsaved entity with its relations left for the service to resolve
   */
  @BeanMapping(nullValueCheckStrategy = NullValueCheckStrategy.ALWAYS)
{%- for r in e.owning_relations %}
  @Mapping(target = "{{ r.name }}", ignore = true)
{%- endfor %}
{%- for i in e.inverse_relations %}
  @Mapping(target = "{{ i.name }}", ignore = true)
{%- endfor %}
  {{ e.name }} toEntity(Create{{ e.name }}Request request);

  /**
   * Maps a persisted {@link {{ e.name }}} to its response with audit metadata.
   *
   * @param entity the entity to map
   * @return the response payload
   */
{%- for r in e.owning_relations %}
{%- if r.is_collection %}
  @Mapping(target = "{{ r.id_field }}", expression = "java(ids(entity.{{ r.getter }}()))")
{%- else %}
  @Mapping(target = "{{ r.id_field }}", source = "{{ r.name }}.id")
{%- endif %}
{%- endfor %}
  {{ e.name }}Response toResponse({{ e.name }} entity);

  /**
   * Applies an update request onto a managed {@link {{ e.name }}}, leaving relations alone.
   *
   * @param request the validated update payload
   * @param entity the managed entity to mutate
   */
  @Mapping(target = "id", ignore = true)
  @Mapping(target = "createdAt", ignore = true)
  @Mapping(target = "updatedAt", ignore = true)
  @Mapping(target = "version", ignore = true)
  @Mapping(target = "deletedAt", ignore = true)
{%- for r in e.owning_relations %}
  @Mapping(target = "{{ r.name }}", ignore = true)
{%- endfor %}
{%- for i in e.inverse_relations %}
  @Mapping(target = "{{ i.name }}", ignore = true)
{%- endfor %}
{{ wrap(2, 'void updateEntityFromRequest(', ['Update' ~ e.name ~ 'Request request', '@MappingTarget ' ~ e.name ~ ' entity'], ');') }}
{%- if many %}

  /**
   * Extracts the ids of the given entities.
   *
   * @param entities the entities, may be {@code null}
   * @return their ids, never {@code null}
   */
  default Set<UUID> ids(Collection<? extends BaseEntity> entities) {
    if (entities == null) {
      return Set.of();
    }
    return entities.stream().map(BaseEntity::getId).collect(Collectors.toSet());
  }
{%- endif %}
}
