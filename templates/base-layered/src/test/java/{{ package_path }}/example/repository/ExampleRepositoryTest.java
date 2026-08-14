package {{ base_package }}.example.repository;

import static org.assertj.core.api.Assertions.assertThat;

import {{ base_package }}.common.config.JpaAuditingConfig;
import {{ base_package }}.example.entity.Example;
import {{ base_package }}.example.entity.ExampleStatus;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.data.jpa.test.autoconfigure.DataJpaTest;
import org.springframework.boot.jdbc.test.autoconfigure.AutoConfigureTestDatabase;
import org.springframework.context.annotation.Import;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Testcontainers
@Import(JpaAuditingConfig.class)
class ExampleRepositoryTest {

  @Container
  static final PostgreSQLContainer<?> postgres =
      new PostgreSQLContainer<>("postgres:16-alpine")
          .withDatabaseName("testdb")
          .withUsername("test")
          .withPassword("test");

  @DynamicPropertySource
  static void configureProperties(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", postgres::getJdbcUrl);
    registry.add("spring.datasource.username", postgres::getUsername);
    registry.add("spring.datasource.password", postgres::getPassword);
  }

  @Autowired ExampleRepository repository;

  @Test
  void findByIdAndDeletedAtIsNull_excludesSoftDeletedRows() {
    Example active = repository.save(Example.builder().name("active-example").build());

    Example deleted = Example.builder().name("deleted-example").build();
    deleted.softDelete();
    deleted = repository.save(deleted);

    assertThat(repository.findByIdAndDeletedAtIsNull(active.getId())).isPresent();
    assertThat(repository.findByIdAndDeletedAtIsNull(deleted.getId())).isEmpty();
  }

  @Test
  void findAllByDeletedAtIsNull_returnsOnlyActiveRowsPaged() {
    repository.save(Example.builder().name("active-1").build());
    repository.save(Example.builder().name("active-2").build());
    repository.save(Example.builder().name("active-3").build());

    Example deleted = Example.builder().name("deleted-1").build();
    deleted.softDelete();
    Example savedDeleted = repository.save(deleted);

    Page<Example> page = repository.findAllByDeletedAtIsNull(PageRequest.of(0, 10));

    assertThat(page.getContent()).hasSize(3);
    assertThat(page.getContent()).extracting(Example::getId).doesNotContain(savedDeleted.getId());
  }

  @Test
  void save_populatesAuditAndVersionFields() {
    Example saved = repository.save(Example.builder().name("audit-check").build());

    assertThat(saved.getId()).isNotNull();
    assertThat(saved.getCreatedAt()).isNotNull();
    assertThat(saved.getUpdatedAt()).isNotNull();
    assertThat(saved.getVersion()).isEqualTo(0L);
    assertThat(saved.getStatus()).isEqualTo(ExampleStatus.ACTIVE);
  }
}
