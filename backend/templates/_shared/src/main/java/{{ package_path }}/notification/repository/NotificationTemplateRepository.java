package {{ base_package }}.notification.repository;

import {{ base_package }}.notification.entity.NotificationTemplate;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

/**
 * Spring Data JPA repository for {@link NotificationTemplate}. Following the template's soft-delete
 * convention, every finder excludes rows with a {@code deleted_at} value, and only active templates
 * are ever used for sending.
 */
public interface NotificationTemplateRepository extends JpaRepository<NotificationTemplate, UUID> {

  /**
   * Finds every active template of a key, across channels and locales.
   *
   * @param templateKey the logical template name
   * @return the active, non-deleted templates; empty if the key is unknown
   */
  List<NotificationTemplate> findByTemplateKeyAndActiveTrueAndDeletedAtIsNull(String templateKey);

  /**
   * Finds the active template for one key, channel and locale.
   *
   * @param templateKey the logical template name
   * @param channel the channel's stored value, such as {@code email}
   * @param locale the two-letter locale
   * @return the template if present, active and not deleted
   */
  Optional<NotificationTemplate>
      findByTemplateKeyAndChannelAndLocaleAndActiveTrueAndDeletedAtIsNull(
          String templateKey, String channel, String locale);
}
