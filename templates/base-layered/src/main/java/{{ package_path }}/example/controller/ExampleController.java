package {{ base_package }}.example.controller;

import {{ base_package }}.common.dto.ApiResponse;
import {{ base_package }}.common.dto.PageResponse;
import {{ base_package }}.example.dto.CreateExampleRequest;
import {{ base_package }}.example.dto.ExampleResponse;
import {{ base_package }}.example.dto.UpdateExampleRequest;
import {{ base_package }}.example.entity.ExampleStatus;
import {{ base_package }}.example.service.ExampleService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import java.net.URI;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;

/**
 * REST entry point for the {@code Example} resource, exposing CRUD operations under {@code
 * /api/v1/examples}. This is the {@code controller} layer of the reference six-package pattern
 * (entity/dto/mapper/repository/service/controller): it owns HTTP concerns only (routing, status
 * codes, request/response wrapping) and delegates all business logic to {@link ExampleService}.
 * When copying this package for a new domain feature, rename the class and mapping path, keep the
 * thin-controller shape, and swap the request/response DTOs and status codes to match the new
 * resource's semantics.
 */
@RestController
@RequestMapping("/api/v1/examples")
@RequiredArgsConstructor
@Tag(name = "Examples", description = "Example resource CRUD endpoints")
@Validated
public class ExampleController {

  private final ExampleService service;

  /**
   * {@code GET /api/v1/examples} - lists non-deleted examples as a page, optionally filtered by
   * {@link ExampleStatus}.
   *
   * @param page page number, zero-based (default {@code 0})
   * @param size page size, 1-100 inclusive (default {@code 20})
   * @param sortBy entity property to sort by (default {@code createdAt})
   * @param sortDirection {@code ASC} or {@code DESC} (default {@code DESC})
   * @param status optional status filter; when omitted all statuses are included
   * @return {@code 200 OK} with the requested page of examples wrapped in {@link ApiResponse}
   */
  @GetMapping
  @Operation(summary = "List examples")
  public ResponseEntity<ApiResponse<PageResponse<ExampleResponse>>> findAll(
      @RequestParam(defaultValue = "0") @Min(0) int page,
      @RequestParam(defaultValue = "20") @Min(1) @Max(100) int size,
      @RequestParam(defaultValue = "createdAt") String sortBy,
      @RequestParam(defaultValue = "DESC") String sortDirection,
      @RequestParam(required = false) ExampleStatus status) {
    PageResponse<ExampleResponse> result =
        service.findAll(page, size, sortBy, sortDirection, status);
    return ResponseEntity.ok(ApiResponse.success("Examples retrieved successfully", result));
  }

  /**
   * {@code GET /api/v1/examples/{id}} - fetches a single example by id.
   *
   * @param id the example id
   * @return {@code 200 OK} with the example wrapped in {@link ApiResponse}. Note: if no non-deleted
   *     example exists with the given id, this method does not itself throw - {@link
   *     ExampleService#findById(UUID)} throws {@code ResourceNotFoundException}, which is
   *     translated to a {@code 404} by the global exception handler.
   */
  @GetMapping("/{id}")
  @Operation(summary = "Get example by id")
  public ResponseEntity<ApiResponse<ExampleResponse>> findById(@PathVariable UUID id) {
    return ResponseEntity.ok(
        ApiResponse.success("Example retrieved successfully", service.findById(id)));
  }

  /**
   * {@code POST /api/v1/examples} - creates a new example.
   *
   * @param request validated creation payload
   * @return {@code 201 Created} with a {@code Location} header pointing at the new resource and the
   *     created example wrapped in {@link ApiResponse}. If an active example with the same name
   *     already exists, the service layer rejects the request with a conflict, translated to {@code
   *     409} by the global exception handler.
   */
  @PostMapping
  @Operation(summary = "Create example")
  public ResponseEntity<ApiResponse<ExampleResponse>> create(
      @Valid @RequestBody CreateExampleRequest request) {
    ExampleResponse created = service.create(request);
    URI location =
        ServletUriComponentsBuilder.fromCurrentRequest()
            .path("/{id}")
            .buildAndExpand(created.getId())
            .toUri();
    return ResponseEntity.created(location)
        .body(ApiResponse.success("Example created successfully", created));
  }

  /**
   * {@code PUT /api/v1/examples/{id}} - updates an existing example's name and status.
   *
   * @param id the example id
   * @param request validated update payload
   * @return {@code 200 OK} with the updated example wrapped in {@link ApiResponse}. As with {@link
   *     #findById(UUID)}, a missing example results in a {@code 404} raised by the service layer
   *     rather than by this method.
   */
  @PutMapping("/{id}")
  @Operation(summary = "Update example")
  public ResponseEntity<ApiResponse<ExampleResponse>> update(
      @PathVariable UUID id, @Valid @RequestBody UpdateExampleRequest request) {
    return ResponseEntity.ok(
        ApiResponse.success("Example updated successfully", service.update(id, request)));
  }

  /**
   * {@code DELETE /api/v1/examples/{id}} - soft-deletes an example (see {@link
   * ExampleService#delete(UUID)}); the row is retained but excluded from future queries.
   *
   * @param id the example id
   * @return {@code 204 No Content} on success. A missing example results in a {@code 404} raised by
   *     the service layer rather than by this method.
   */
  @DeleteMapping("/{id}")
  @Operation(summary = "Delete example")
  public ResponseEntity<Void> delete(@PathVariable UUID id) {
    service.delete(id);
    return ResponseEntity.noContent().build();
  }
}
