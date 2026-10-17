package {{ base_package }}.notification.entity;

import {{ base_package }}.common.entity.BaseEntity;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import java.util.UUID;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/**
 * JPA entity backing {@code notification_preferences}: a recipient's channel switches. A recipient
 * without a row has the defaults (everything on).
 */
@Entity
@Table(name = "notification_preferences")
@Getter
@Setter
@NoArgsConstructor
public class NotificationPreference extends BaseEntity {

  /** The recipient these preferences belong to. */
  @Column(name = "recipient_id", nullable = false, unique = true)
  private UUID recipientId;

  /** Whether email notifications are enabled. */
  @Column(name = "email_enabled", nullable = false)
  private boolean emailEnabled = true;

  /**
   * Constructs a new, unsaved preference row with the defaults.
   *
   * @param recipientId the owning recipient
   */
  @Builder
  public NotificationPreference(UUID recipientId) {
    this.recipientId = recipientId;
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof NotificationPreference other)) return false;
    return getId() != null && getId().equals(other.getId());
  }

  @Override
  public int hashCode() {
    return getClass().hashCode();
  }
}
