package {{ base_package }}.example.mapper;

import static org.assertj.core.api.Assertions.assertThat;

import {{ base_package }}.example.dto.CreateExampleRequest;
import {{ base_package }}.example.dto.ExampleResponse;
import {{ base_package }}.example.dto.UpdateExampleRequest;
import {{ base_package }}.example.entity.Example;
import {{ base_package }}.example.entity.ExampleStatus;
import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class ExampleMapperTest {

  private final ExampleMapper mapper = new ExampleMapperImpl();

  @Test
  void toEntity_mapsNameAndDefaultsStatusToActive() {
    CreateExampleRequest request = CreateExampleRequest.builder().name("Widget").build();

    Example entity = mapper.toEntity(request);

    assertThat(entity.getName()).isEqualTo("Widget");
    assertThat(entity.getStatus()).isEqualTo(ExampleStatus.ACTIVE);
  }

  @Test
  void toResponse_mapsAllFields() {
    Example entity = Example.builder().name("Widget").status(ExampleStatus.ARCHIVED).build();
    UUID id = UUID.randomUUID();
    Instant createdAt = Instant.now().minusSeconds(60);
    Instant updatedAt = Instant.now();
    entity.setId(id);
    entity.setCreatedAt(createdAt);
    entity.setUpdatedAt(updatedAt);
    entity.setVersion(3L);

    ExampleResponse response = mapper.toResponse(entity);

    assertThat(response.getId()).isEqualTo(id);
    assertThat(response.getName()).isEqualTo("Widget");
    assertThat(response.getStatus()).isEqualTo(ExampleStatus.ARCHIVED);
    assertThat(response.getCreatedAt()).isEqualTo(createdAt);
    assertThat(response.getUpdatedAt()).isEqualTo(updatedAt);
    assertThat(response.getVersion()).isEqualTo(3L);
  }

  @Test
  void updateEntityFromRequest_appliesNameAndStatusInPlace() {
    Example entity = Example.builder().name("Original").status(ExampleStatus.ACTIVE).build();
    UpdateExampleRequest request =
        UpdateExampleRequest.builder().name("Renamed").status(ExampleStatus.ARCHIVED).build();

    mapper.updateEntityFromRequest(request, entity);

    assertThat(entity.getName()).isEqualTo("Renamed");
    assertThat(entity.getStatus()).isEqualTo(ExampleStatus.ARCHIVED);
  }
}
