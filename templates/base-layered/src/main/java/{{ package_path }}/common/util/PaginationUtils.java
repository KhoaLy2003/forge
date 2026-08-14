package {{ base_package }}.common.util;

import {{ base_package }}.common.dto.PageResponse;
import {{ base_package }}.common.dto.PaginationMeta;
import java.util.List;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;

/**
 * Static helpers shared by controllers/services for translating raw pagination request parameters
 * into a Spring Data {@link Pageable}, and translating a returned {@link
 * org.springframework.data.domain.Page} back into this API's {@link PageResponse} envelope. Not
 * instantiable.
 */
public final class PaginationUtils {

  private PaginationUtils() {}

  /**
   * Builds a {@link Pageable} from raw request parameters.
   *
   * <p>{@code sortDirection} is matched case-insensitively against {@code "ASC"}; any other value
   * (including {@code null}, typos, or {@code "DESC"}) falls back to descending order. Callers that
   * need ascending order must pass exactly {@code "asc"}/{@code "ASC"}.
   *
   * @param page zero-based page index
   * @param size number of items per page
   * @param sortBy the entity property to sort by
   * @param sortDirection {@code "ASC"} (case-insensitive) for ascending order; anything else yields
   *     descending order
   * @return a {@link Pageable} configured with the given page, size, and sort
   */
  public static Pageable createPageable(int page, int size, String sortBy, String sortDirection) {
    Sort.Direction direction =
        "ASC".equalsIgnoreCase(sortDirection) ? Sort.Direction.ASC : Sort.Direction.DESC;
    return PageRequest.of(page, size, Sort.by(direction, sortBy));
  }

  /**
   * Wraps an already-mapped content list together with pagination metadata derived from the source
   * {@link Page} into a {@link PageResponse}. The {@code content} list is expected to be the
   * caller's DTO-mapped equivalent of {@code page}'s elements (allowing the raw entity page and the
   * response DTO type to differ), and is not re-derived from {@code page} here.
   *
   * @param page the Spring Data page the metadata (page number, size, totals, next/prev flags) is
   *     derived from
   * @param content the response payload items to attach, typically {@code page}'s content mapped to
   *     a DTO type
   * @param <T> the element type of {@code content}
   * @return a {@link PageResponse} pairing {@code content} with metadata derived from {@code page}
   */
  public static <T> PageResponse<T> toPageResponse(Page<?> page, List<T> content) {
    PaginationMeta meta =
        PaginationMeta.builder()
            .page(page.getNumber())
            .limit(page.getSize())
            .total(page.getTotalElements())
            .totalPages(page.getTotalPages())
            .hasNext(page.hasNext())
            .hasPrev(page.hasPrevious())
            .build();
    return PageResponse.<T>builder().data(content).pagination(meta).build();
  }
}
