package {{ base_package }}.example.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Inbound payload for {@code POST /api/v1/examples}. This is the request-side {@code dto} of the
 * reference six-package pattern: it exposes only the fields a client may supply on creation
 * (deliberately excluding server-managed fields like id, status, and audit timestamps) and carries
 * the Bean Validation constraints enforced before the controller hands off to the service layer.
 * When adapting this package for a new domain, replace the fields and constraints to match what
 * that resource accepts on create.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CreateExampleRequest {

  @NotBlank(message = "Name is required")
  @Size(max = 120, message = "Name must be at most 120 characters")
  private String name;
}
