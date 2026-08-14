package {{ base_package }}.example.dto;

import {{ base_package }}.example.entity.ExampleStatus;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Inbound payload for {@code PUT /api/v1/examples/{id}}. Another request-side {@code dto} of the
 * reference six-package pattern, distinct from {@link CreateExampleRequest} because update allows
 * changing fields (like {@code status}) that creation does not accept and defaults instead. When
 * adapting this package for a new domain, keep create and update requests as separate DTOs whenever
 * their allowed fields diverge.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UpdateExampleRequest {

  @NotBlank(message = "Name is required")
  @Size(max = 120, message = "Name must be at most 120 characters")
  private String name;

  @NotNull(message = "Status is required")
  private ExampleStatus status;
}
