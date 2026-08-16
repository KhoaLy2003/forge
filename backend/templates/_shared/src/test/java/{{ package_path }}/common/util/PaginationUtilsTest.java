package {{ base_package }}.common.util;

import static org.assertj.core.api.Assertions.assertThat;

import {{ base_package }}.common.dto.PageResponse;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;

class PaginationUtilsTest {

  @Test
  void createPageable_sortsAscendingWhenDirectionIsAsc() {
    Pageable pageable = PaginationUtils.createPageable(0, 20, "name", "ASC");

    Sort.Order order = pageable.getSort().getOrderFor("name");
    assertThat(order).isNotNull();
    assertThat(order.getDirection()).isEqualTo(Sort.Direction.ASC);
  }

  @Test
  void createPageable_defaultsToDescendingForUnrecognizedDirection() {
    Pageable pageable = PaginationUtils.createPageable(0, 20, "name", "bogus");

    Sort.Order order = pageable.getSort().getOrderFor("name");
    assertThat(order).isNotNull();
    assertThat(order.getDirection()).isEqualTo(Sort.Direction.DESC);
  }

  @Test
  void toPageResponse_mapsPageMetadataCorrectly() {
    Page<String> fixture = new PageImpl<>(List.of("a", "b"), PageRequest.of(0, 2), 5);

    PageResponse<String> result = PaginationUtils.toPageResponse(fixture, List.of("x", "y"));

    assertThat(result.getData()).isEqualTo(List.of("x", "y"));
    assertThat(result.getPagination().getPage()).isEqualTo(0);
    assertThat(result.getPagination().getLimit()).isEqualTo(2);
    assertThat(result.getPagination().getTotal()).isEqualTo(5);
    assertThat(result.getPagination().getTotalPages()).isEqualTo(3);
    assertThat(result.getPagination().isHasNext()).isTrue();
    assertThat(result.getPagination().isHasPrev()).isFalse();
  }
}
