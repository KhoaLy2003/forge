package {{ base_package }}.example.dto;

import {{ base_package }}.example.entity.ExampleStatus;
import java.time.Instant;
import java.util.UUID;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Outbound payload returned by every {@code Example} endpoint. This is the response-side {@code
 * dto} of the reference six-package pattern: it mirrors the entity's client-visible state
 * (including audit and optimistic-locking metadata) while never exposing the entity itself over the
 * wire. {@code version} is surfaced so clients performing subsequent updates can reason about
 * optimistic locking. When adapting this package for a new domain, shape this class around what
 * that resource should reveal to API consumers.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ExampleResponse {

  private UUID id;
  private String name;
  private ExampleStatus status;
  private Instant createdAt;
  private Instant updatedAt;
  private Long version;
}
