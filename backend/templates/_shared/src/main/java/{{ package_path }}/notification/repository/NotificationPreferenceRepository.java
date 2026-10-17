package {{ base_package }}.notification.repository;

import {{ base_package }}.notification.entity.NotificationPreference;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

/** Spring Data JPA repository for {@link NotificationPreference}. */
public interface NotificationPreferenceRepository
    extends JpaRepository<NotificationPreference, UUID> {

  /**
   * Finds a recipient's preferences.
   *
   * @param recipientId the recipient
   * @return the preferences if the recipient has changed any, otherwise empty (meaning defaults)
   */
  Optional<NotificationPreference> findByRecipientIdAndDeletedAtIsNull(UUID recipientId);

  /**
   * Physically removes a recipient's preferences (used when the recipient is purged).
   *
   * @param recipientId the recipient
   */
  void deleteByRecipientId(UUID recipientId);
}
