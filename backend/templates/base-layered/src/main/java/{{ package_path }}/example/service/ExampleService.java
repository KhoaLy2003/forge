package {{ base_package }}.example.service;

import {{ base_package }}.common.dto.PageResponse;
import {{ base_package }}.common.exception.ConflictException;
import {{ base_package }}.common.exception.ResourceNotFoundException;
import {{ base_package }}.example.dto.CreateExampleRequest;
import {{ base_package }}.example.dto.ExampleResponse;
import {{ base_package }}.example.dto.UpdateExampleRequest;
import {{ base_package }}.example.entity.ExampleStatus;
import java.util.UUID;

/**
 * Business operations for the {@code Example} resource. This is the {@code service} (contract) half
 * of the reference six-package pattern's service layer: it defines what the domain can do,
 * independent of HTTP or persistence concerns, and is implemented by {@link ExampleServiceImpl}.
 * When copying this package for a new domain, keep the controller depending on this interface
 * rather than the implementation.
 */
public interface ExampleService {

  /**
   * Retrieves a single non-deleted example by id.
   *
   * @param id the example id
   * @return the matching example
   * @throws ResourceNotFoundException if no non-deleted example exists with the given id
   */
  ExampleResponse findById(UUID id);

  /**
   * Retrieves a page of non-deleted examples, optionally filtered by status.
   *
   * @param page zero-based page number
   * @param size page size
   * @param sortBy property to sort by
   * @param sortDirection {@code ASC} or {@code DESC}
   * @param status optional status filter; when {@code null}, all statuses are included
   * @return the requested page of examples
   */
  PageResponse<ExampleResponse> findAll(
      int page, int size, String sortBy, String sortDirection, ExampleStatus status);

  /**
   * Creates a new example after checking for a name conflict.
   *
   * @param request the validated creation payload
   * @return the created example
   * @throws ConflictException if a non-deleted example with the same name already exists
   */
  ExampleResponse create(CreateExampleRequest request);

  /**
   * Updates an existing example's mutable fields.
   *
   * @param id the example id
   * @param request the validated update payload
   * @return the updated example
   * @throws ResourceNotFoundException if no non-deleted example exists with the given id
   */
  ExampleResponse update(UUID id, UpdateExampleRequest request);

  /**
   * Soft-deletes an example: the row is retained with {@code deletedAt} set, rather than being
   * physically removed, so it is excluded from all future soft-delete-aware queries.
   *
   * @param id the example id
   * @throws ResourceNotFoundException if no non-deleted example exists with the given id
   */
  void delete(UUID id);
}
