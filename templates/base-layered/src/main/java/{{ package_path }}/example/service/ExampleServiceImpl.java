package {{ base_package }}.example.service;

import {{ base_package }}.common.dto.PageResponse;
import {{ base_package }}.common.exception.ConflictException;
import {{ base_package }}.common.exception.ResourceNotFoundException;
import {{ base_package }}.common.util.PaginationUtils;
import {{ base_package }}.example.dto.CreateExampleRequest;
import {{ base_package }}.example.dto.ExampleResponse;
import {{ base_package }}.example.dto.UpdateExampleRequest;
import {{ base_package }}.example.entity.Example;
import {{ base_package }}.example.entity.ExampleStatus;
import {{ base_package }}.example.mapper.ExampleMapper;
import {{ base_package }}.example.repository.ExampleRepository;
import java.util.List;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Default implementation of {@link ExampleService}. This is the {@code service} (implementation)
 * half of the reference six-package pattern's service layer: it owns transaction boundaries,
 * orchestrates repository and mapper calls, and translates business-rule violations (not found,
 * duplicate name) into the shared exception types handled by the global exception handler. The
 * class is annotated {@code @Transactional(readOnly = true)} by default; individual mutating
 * methods override this with a writable {@code @Transactional}. When copying this package for a new
 * domain, keep this read-only-by-default / opt-in-write pattern.
 */
@Service
@RequiredArgsConstructor
@Slf4j
@Transactional(readOnly = true)
public class ExampleServiceImpl implements ExampleService {

  private final ExampleRepository repository;
  private final ExampleMapper mapper;

  /**
   * {@inheritDoc}
   *
   * <p>Looks up the entity via the soft-delete-aware repository query and maps it to a response,
   * throwing if no non-deleted example matches.
   */
  @Override
  @Transactional(readOnly = true)
  public ExampleResponse findById(UUID id) {
    Example entity =
        repository
            .findByIdAndDeletedAtIsNull(id)
            .orElseThrow(() -> new ResourceNotFoundException("Example not found with id: " + id));
    return mapper.toResponse(entity);
  }

  /**
   * {@inheritDoc}
   *
   * <p>Delegates paging/sorting construction to {@code PaginationUtils} and chooses between the
   * status-filtered and unfiltered repository query based on whether {@code status} was supplied.
   */
  @Override
  @Transactional(readOnly = true)
  public PageResponse<ExampleResponse> findAll(
      int page, int size, String sortBy, String sortDirection, ExampleStatus status) {
    Pageable pageable = PaginationUtils.createPageable(page, size, sortBy, sortDirection);
    Page<Example> result =
        status != null
            ? repository.findByStatusAndDeletedAtIsNull(status, pageable)
            : repository.findAllByDeletedAtIsNull(pageable);
    List<ExampleResponse> content = result.getContent().stream().map(mapper::toResponse).toList();
    return PaginationUtils.toPageResponse(result, content);
  }

  /**
   * {@inheritDoc}
   *
   * <p>Rejects the request up front if a non-deleted example with the same name already exists,
   * before mapping and persisting the new entity.
   */
  @Override
  @Transactional
  public ExampleResponse create(CreateExampleRequest request) {
    if (repository.existsByNameAndDeletedAtIsNull(request.getName())) {
      throw new ConflictException("Example with name '" + request.getName() + "' already exists");
    }
    Example saved = repository.save(mapper.toEntity(request));
    log.info("Example created with id: {}", saved.getId());
    return mapper.toResponse(saved);
  }

  /**
   * {@inheritDoc}
   *
   * <p>Loads the managed entity, applies the update in place via the mapper, and saves it. Because
   * {@code Example} carries a JPA {@code @Version} column, a concurrent update between the load and
   * this save results in Hibernate throwing an optimistic-locking failure on flush rather than
   * silently overwriting the other change.
   */
  @Override
  @Transactional
  public ExampleResponse update(UUID id, UpdateExampleRequest request) {
    Example entity =
        repository
            .findByIdAndDeletedAtIsNull(id)
            .orElseThrow(() -> new ResourceNotFoundException("Example not found with id: " + id));
    mapper.updateEntityFromRequest(request, entity);
    Example saved = repository.save(entity);
    log.info("Example updated: {}", id);
    return mapper.toResponse(saved);
  }

  /**
   * {@inheritDoc}
   *
   * <p>Performs a soft delete: marks {@code deletedAt} on the entity and saves it, rather than
   * calling {@code repository.delete(...)}, so the row remains for audit purposes but is excluded
   * from every soft-delete-aware repository query going forward.
   */
  @Override
  @Transactional
  public void delete(UUID id) {
    Example entity =
        repository
            .findByIdAndDeletedAtIsNull(id)
            .orElseThrow(() -> new ResourceNotFoundException("Example not found with id: " + id));
    entity.softDelete();
    repository.save(entity);
    log.info("Example deleted: {}", id);
  }
}
