package {{ base_package }}.common.dto;

import {{ base_package }}.common.util.PaginationUtils;
import java.util.List;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Response shape for paginated list endpoints: the page of items alongside the {@link
 * PaginationMeta} describing where that page sits in the full result set. Built via {@link
 * PaginationUtils#toPageResponse}, which derives the metadata from a Spring Data {@link
 * org.springframework.data.domain.Page}.
 *
 * @param <T> the element type of the paged {@code data} list
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PageResponse<T> {

  private List<T> data;
  private PaginationMeta pagination;
}
