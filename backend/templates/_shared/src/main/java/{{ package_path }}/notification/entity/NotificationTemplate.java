package {{ base_package }}.notification.entity;

import {{ base_package }}.common.entity.BaseEntity;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/**
 * JPA entity backing {@code notification_templates}: the plain-text subject and body of one
 * (template key, channel, locale) with double-brace placeholders. {@code templateVersion} is a
 * human-visible edit counter; the {@code @Version} column of {@link BaseEntity} is separate.
 */
@Entity
@Table(name = "notification_templates")
@Getter
@Setter
@NoArgsConstructor
public class NotificationTemplate extends BaseEntity {

  /** Logical template name such as {@code welcome}. */
  @Column(name = "template_key", nullable = false, length = 80)
  private String templateKey;

  /** {@code in_app} or {@code email}. */
  @Column(name = "channel", nullable = false, length = 10)
  private String channel;

  /** Two-letter locale such as {@code en}. */
  @Column(name = "locale", nullable = false, length = 2)
  private String locale;

  /** Email subject, or the in-app title. */
  @Column(name = "subject", nullable = false, length = 200)
  private String subject;

  /** Message body. */
  @Column(name = "body", nullable = false, columnDefinition = "TEXT")
  private String body;

  /** Incremented whenever the wording is edited. */
  @Column(name = "template_version", nullable = false)
  private int templateVersion = 1;

  /** Inactive templates are ignored when sending. */
  @Column(name = "active", nullable = false)
  private boolean active = true;

  /**
   * Constructs a new, unsaved template.
   *
   * @param templateKey logical template name
   * @param channel {@code in_app} or {@code email}
   * @param locale two-letter locale
   * @param subject title or email subject
   * @param body message body
   */
  @Builder
  public NotificationTemplate(
      String templateKey, String channel, String locale, String subject, String body) {
    this.templateKey = templateKey;
    this.channel = channel;
    this.locale = locale;
    this.subject = subject;
    this.body = body;
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof NotificationTemplate other)) return false;
    return getId() != null && getId().equals(other.getId());
  }

  @Override
  public int hashCode() {
    return getClass().hashCode();
  }
}
