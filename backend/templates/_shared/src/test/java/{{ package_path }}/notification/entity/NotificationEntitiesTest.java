package {{ base_package }}.notification.entity;

import static org.assertj.core.api.Assertions.assertThat;

import {{ base_package }}.common.entity.BaseEntity;
import jakarta.persistence.Column;
import jakarta.persistence.Table;
import java.io.IOException;
import java.io.InputStream;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.Test;
import org.springframework.core.io.ClassPathResource;

/**
 * Guards the entity mappings against drifting from the Liquibase migration without needing a
 * database: every mapped column must exist in the table's {@code CREATE TABLE} statement.
 */
class NotificationEntitiesTest {

  private static final String MIGRATION = "db/changelog/002-create-notifications.sql";

  private static String migration() throws IOException {
    try (InputStream in = new ClassPathResource(MIGRATION).getInputStream()) {
      return new String(in.readAllBytes(), StandardCharsets.UTF_8);
    }
  }

  private static String createTableBlock(String sql, String table) {
    Matcher matcher =
        Pattern.compile("CREATE TABLE " + table + "\\b(.*?)\\n\\);", Pattern.DOTALL).matcher(sql);
    assertThat(matcher.find()).as("CREATE TABLE " + table).isTrue();
    return matcher.group(1);
  }

  private static List<String> mappedColumns(Class<?> entity) {
    List<String> columns = new ArrayList<>();
    for (Class<?> type = entity; type != Object.class; type = type.getSuperclass()) {
      for (Field field : type.getDeclaredFields()) {
        Column column = field.getAnnotation(Column.class);
        if (column != null) {
          columns.add(column.name());
        }
      }
    }
    return columns;
  }

  private static void assertEveryColumnExistsInMigration(Class<?> entity) throws IOException {
    String table = entity.getAnnotation(Table.class).name();
    String block = createTableBlock(migration(), table);

    assertThat(mappedColumns(entity)).isNotEmpty();
    for (String column : mappedColumns(entity)) {
      assertThat(block).as(table + "." + column).containsPattern("\\b" + column + "\\b");
    }
  }

  @Test
  void template_isMappedToNotificationTemplatesAndMatchesTheMigration() throws IOException {
    assertThat(NotificationTemplate.class.getAnnotation(Table.class).name())
        .isEqualTo("notification_templates");
    assertThat(BaseEntity.class).isAssignableFrom(NotificationTemplate.class);

    assertEveryColumnExistsInMigration(NotificationTemplate.class);
  }

  @Test
  void preference_isMappedToNotificationPreferencesAndMatchesTheMigration() throws IOException {
    assertThat(NotificationPreference.class.getAnnotation(Table.class).name())
        .isEqualTo("notification_preferences");
    assertThat(BaseEntity.class).isAssignableFrom(NotificationPreference.class);

    assertEveryColumnExistsInMigration(NotificationPreference.class);
  }

  @Test
  void template_builderSetsFieldsAndDefaultsToActiveVersionOne() {
    NotificationTemplate template =
        NotificationTemplate.builder()
            .templateKey("welcome")
            .channel("email")
            .locale("en")
            .subject("Hi")
            .body("Body")
            .build();

    assertThat(template.getTemplateKey()).isEqualTo("welcome");
    assertThat(template.getChannel()).isEqualTo("email");
    assertThat(template.getLocale()).isEqualTo("en");
    assertThat(template.getSubject()).isEqualTo("Hi");
    assertThat(template.getBody()).isEqualTo("Body");
    assertThat(template.isActive()).isTrue();
    assertThat(template.getTemplateVersion()).isEqualTo(1);
  }

  @Test
  void preference_defaultsToEmailEnabled() {
    UUID recipient = UUID.randomUUID();

    NotificationPreference preference =
        NotificationPreference.builder().recipientId(recipient).build();

    assertThat(preference.getRecipientId()).isEqualTo(recipient);
    assertThat(preference.isEmailEnabled()).isTrue();
  }

  @Test
  void entitiesAreEqualOnlyByNonNullId() {
    NotificationPreference first = new NotificationPreference();
    NotificationPreference second = new NotificationPreference();

    assertThat(first).isNotEqualTo(second);
    assertThat(first).isEqualTo(first);
    assertThat(first.hashCode()).isEqualTo(second.hashCode());
  }
}
