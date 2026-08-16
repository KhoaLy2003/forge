package {{ base_package }}.example.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import {{ base_package }}.common.exception.ConflictException;
import {{ base_package }}.common.exception.ResourceNotFoundException;
import {{ base_package }}.example.dto.CreateExampleRequest;
import {{ base_package }}.example.dto.ExampleResponse;
import {{ base_package }}.example.dto.UpdateExampleRequest;
import {{ base_package }}.example.entity.Example;
import {{ base_package }}.example.entity.ExampleStatus;
import {{ base_package }}.example.mapper.ExampleMapper;
import {{ base_package }}.example.repository.ExampleRepository;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;

@ExtendWith(MockitoExtension.class)
class ExampleServiceImplTest {

  @Mock private ExampleRepository repository;

  @Mock private ExampleMapper mapper;

  @InjectMocks private ExampleServiceImpl service;

  @Test
  void findById_whenFound_returnsResponse() {
    UUID id = UUID.randomUUID();
    Example entity = Example.builder().name("Widget").build();
    ExampleResponse fixture = ExampleResponse.builder().id(id).name("Widget").build();

    when(repository.findByIdAndDeletedAtIsNull(id)).thenReturn(Optional.of(entity));
    when(mapper.toResponse(entity)).thenReturn(fixture);

    ExampleResponse result = service.findById(id);

    assertThat(result).isEqualTo(fixture);
  }

  @Test
  void findById_whenNotFound_throwsResourceNotFoundException() {
    UUID id = UUID.randomUUID();
    when(repository.findByIdAndDeletedAtIsNull(id)).thenReturn(Optional.empty());

    assertThrows(ResourceNotFoundException.class, () -> service.findById(id));
  }

  @Test
  void findAll_withoutStatusFilter_queriesUnfilteredAndReturnsPage() {
    Example entity = Example.builder().name("Widget").build();
    Pageable pageable = PageRequest.of(0, 20);
    when(repository.findAllByDeletedAtIsNull(any()))
        .thenReturn(new PageImpl<>(List.of(entity), pageable, 1));
    when(mapper.toResponse(entity)).thenReturn(ExampleResponse.builder().name("Widget").build());

    var result = service.findAll(0, 20, "createdAt", "DESC", null);

    assertThat(result.getData()).hasSize(1);
    verify(repository).findAllByDeletedAtIsNull(any());
    verify(repository, never()).findByStatusAndDeletedAtIsNull(any(), any());
  }

  @Test
  void findAll_withStatusFilter_queriesFilteredAndReturnsPage() {
    Example entity = Example.builder().name("Widget").status(ExampleStatus.ACTIVE).build();
    Pageable pageable = PageRequest.of(0, 20);
    when(repository.findByStatusAndDeletedAtIsNull(any(), any()))
        .thenReturn(new PageImpl<>(List.of(entity), pageable, 1));
    when(mapper.toResponse(entity)).thenReturn(ExampleResponse.builder().name("Widget").build());

    var result = service.findAll(0, 20, "createdAt", "DESC", ExampleStatus.ACTIVE);

    assertThat(result.getData()).hasSize(1);
    verify(repository).findByStatusAndDeletedAtIsNull(any(), any());
  }

  @Test
  void create_whenNameIsUnique_savesAndReturnsResponse() {
    CreateExampleRequest request = CreateExampleRequest.builder().name("Widget").build();
    Example toSave = Example.builder().name("Widget").build();
    Example saved = Example.builder().name("Widget").build();
    ExampleResponse fixture = ExampleResponse.builder().name("Widget").build();

    when(repository.existsByNameAndDeletedAtIsNull("Widget")).thenReturn(false);
    when(mapper.toEntity(request)).thenReturn(toSave);
    when(repository.save(toSave)).thenReturn(saved);
    when(mapper.toResponse(saved)).thenReturn(fixture);

    ExampleResponse result = service.create(request);

    assertThat(result).isEqualTo(fixture);
    verify(repository, times(1)).save(toSave);
  }

  @Test
  void create_whenNameAlreadyExists_throwsConflictException() {
    CreateExampleRequest request = CreateExampleRequest.builder().name("Widget").build();
    when(repository.existsByNameAndDeletedAtIsNull("Widget")).thenReturn(true);

    assertThrows(ConflictException.class, () -> service.create(request));
    verify(repository, never()).save(any());
  }

  @Test
  void update_whenFound_appliesMapperAndSaves() {
    UUID id = UUID.randomUUID();
    Example entity = Example.builder().name("Widget").build();
    UpdateExampleRequest request =
        UpdateExampleRequest.builder().name("Renamed").status(ExampleStatus.ARCHIVED).build();

    when(repository.findByIdAndDeletedAtIsNull(id)).thenReturn(Optional.of(entity));
    when(repository.save(entity)).thenReturn(entity);
    when(mapper.toResponse(entity)).thenReturn(ExampleResponse.builder().id(id).build());

    service.update(id, request);

    verify(mapper).updateEntityFromRequest(request, entity);
    verify(repository).save(entity);
  }

  @Test
  void update_whenNotFound_throwsResourceNotFoundException() {
    UUID id = UUID.randomUUID();
    UpdateExampleRequest request = UpdateExampleRequest.builder().name("Renamed").build();
    when(repository.findByIdAndDeletedAtIsNull(id)).thenReturn(Optional.empty());

    assertThrows(ResourceNotFoundException.class, () -> service.update(id, request));
    verify(repository, never()).save(any());
  }

  @Test
  void delete_whenFound_softDeletesAndSaves() {
    UUID id = UUID.randomUUID();
    Example entity = Example.builder().name("Widget").build();

    when(repository.findByIdAndDeletedAtIsNull(id)).thenReturn(Optional.of(entity));

    service.delete(id);

    assertThat(entity.isDeleted()).isTrue();
    verify(repository).save(entity);
  }

  @Test
  void delete_whenNotFound_throwsResourceNotFoundException() {
    UUID id = UUID.randomUUID();
    when(repository.findByIdAndDeletedAtIsNull(id)).thenReturn(Optional.empty());

    assertThrows(ResourceNotFoundException.class, () -> service.delete(id));
    verify(repository, never()).save(any());
  }
}
