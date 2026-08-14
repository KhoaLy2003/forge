package {{ base_package }}.example.repository;

import {{ base_package }}.example.entity.Example;
import {{ base_package }}.example.entity.ExampleStatus;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

/**
 * Spring Data JPA repository for {@link Example}. This is the {@code repository} layer of the
 * reference six-package pattern: plain {@code JpaRepository} inheritance plus derived query
 * methods, with no custom implementation needed. Every query here is suffixed {@code
 * AndDeletedAtIsNull} - this is the soft-delete convention used throughout the template: rows are
 * never physically removed (see {@code BaseEntity#softDelete()}), so every read path must
 * explicitly exclude deleted rows rather than relying on a delete actually removing them from the
 * table. When copying this package for a new domain that also soft-deletes, keep this suffix on
 * every finder/exists query added.
 */
public interface ExampleRepository extends JpaRepository<Example, UUID> {

  /**
   * Finds a non-deleted example by id.
   *
   * @param id the example id
   * @return the example if present and not soft-deleted, otherwise empty
   */
  Optional<Example> findByIdAndDeletedAtIsNull(UUID id);

  /**
   * Lists all non-deleted examples as a page, regardless of status.
   *
   * @param pageable page/size/sort request
   * @return the requested page of non-deleted examples
   */
  Page<Example> findAllByDeletedAtIsNull(Pageable pageable);

  /**
   * Lists non-deleted examples filtered by status, as a page.
   *
   * @param status the status to filter by
   * @param pageable page/size/sort request
   * @return the requested page of matching, non-deleted examples
   */
  Page<Example> findByStatusAndDeletedAtIsNull(ExampleStatus status, Pageable pageable);

  /**
   * Checks whether a non-deleted example with the given name already exists, used by the service
   * layer to enforce a duplicate-name conflict on create.
   *
   * @param name the name to check
   * @return {@code true} if a non-deleted example with this name exists
   */
  boolean existsByNameAndDeletedAtIsNull(String name);
}
