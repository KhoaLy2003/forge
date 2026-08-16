package {{ base_package }}.common.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Pagination metadata attached to a {@link PageResponse}: current page, page size, total item count
 * and page count, and next/previous-page availability flags, so clients can render pagination
 * controls without recomputing them from raw totals.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PaginationMeta {

  private int page;
  private int limit;
  private long total;
  private int totalPages;
  private boolean hasNext;
  private boolean hasPrev;
}
