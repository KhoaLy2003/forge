package {{ base_package }}.notification.repository;

import static org.assertj.core.api.Assertions.assertThat;

import {{ base_package }}.notification.entity.NotificationPreference;
import {{ base_package }}.notification.entity.NotificationTemplate;
import java.lang.reflect.Method;
import java.util.Arrays;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.data.repository.query.parser.PartTree;

/**
 * Parses every derived query method name with Spring Data's own parser, so a misspelled property
 * fails here instead of when the application context starts. No database is needed.
 */
class NotificationRepositoriesTest {

  private static List<Method> derivedQueries(Class<?> repository) {
    return Arrays.stream(repository.getDeclaredMethods())
        .filter(method -> method.getName().matches("(find|delete|count|exists)By.*"))
        .toList();
  }

  @Test
  void templateRepositoryQueryNamesAreValidForTheEntity() {
    List<Method> methods = derivedQueries(NotificationTemplateRepository.class);

    assertThat(methods).hasSize(2);
    for (Method method : methods) {
      assertThat(new PartTree(method.getName(), NotificationTemplate.class)).isNotNull();
    }
  }

  @Test
  void preferenceRepositoryQueryNamesAreValidForTheEntity() {
    List<Method> methods = derivedQueries(NotificationPreferenceRepository.class);

    assertThat(methods).hasSize(2);
    for (Method method : methods) {
      assertThat(new PartTree(method.getName(), NotificationPreference.class)).isNotNull();
    }
  }

  @Test
  void everyFinderExcludesSoftDeletedRows() {
    for (Class<?> repository :
        List.of(NotificationTemplateRepository.class, NotificationPreferenceRepository.class)) {
      for (Method method : derivedQueries(repository)) {
        if (method.getName().startsWith("find")) {
          assertThat(method.getName()).as(method.getName()).endsWith("AndDeletedAtIsNull");
        }
      }
    }
  }
}
