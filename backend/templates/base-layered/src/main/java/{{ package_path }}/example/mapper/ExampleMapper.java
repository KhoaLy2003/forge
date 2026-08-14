package {{ base_package }}.example.mapper;

import {{ base_package }}.example.dto.CreateExampleRequest;
import {{ base_package }}.example.dto.ExampleResponse;
import {{ base_package }}.example.dto.UpdateExampleRequest;
import {{ base_package }}.example.entity.Example;
import {{ base_package }}.example.entity.ExampleStatus;
import org.mapstruct.Mapper;
import org.mapstruct.MappingTarget;
import org.mapstruct.ReportingPolicy;

/**
 * MapStruct mapper converting between {@link Example} and its request/response DTOs. This is the
 * {@code mapper} layer of the reference six-package pattern: the implementation is generated at
 * compile time by the MapStruct annotation processor, so this interface only declares the mapping
 * contract. {@code unmappedTargetPolicy = IGNORE} silences warnings for target fields intentionally
 * left unset by a given mapping (e.g. audit/id fields on {@code toEntity}). When copying this
 * package for a new domain, add one method per direction actually needed and keep intentional field
 * omissions documented here.
 */
@Mapper(componentModel = "spring", unmappedTargetPolicy = ReportingPolicy.IGNORE)
public interface ExampleMapper {

  /**
   * Maps a creation request to a new, transient {@link Example}. {@code status} is deliberately not
   * part of {@link CreateExampleRequest} and is left unset here so the entity's field default
   * ({@link ExampleStatus#ACTIVE}) applies; id, audit timestamps, and version are likewise left for
   * JPA/Hibernate to populate on persist.
   *
   * @param request the validated creation payload
   * @return a new, unsaved {@link Example} ready to be passed to the repository
   */
  Example toEntity(CreateExampleRequest request);

  /**
   * Maps a persisted {@link Example} to its outbound representation, copying all client-visible
   * fields including audit metadata and optimistic-locking version.
   *
   * @param entity the entity to map
   * @return the corresponding {@link ExampleResponse}
   */
  ExampleResponse toResponse(Example entity);

  /**
   * Applies an update request's fields onto an existing, managed {@link Example} in place (rather
   * than constructing a new instance), so JPA dirty-checking and the {@code @Version}
   * optimistic-lock check apply on the subsequent save.
   *
   * @param request the validated update payload
   * @param entity the managed entity to mutate
   */
  void updateEntityFromRequest(UpdateExampleRequest request, @MappingTarget Example entity);
}
