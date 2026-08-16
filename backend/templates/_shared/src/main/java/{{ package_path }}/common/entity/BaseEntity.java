package {{ base_package }}.common.entity;

import {{ base_package }}.common.config.JpaAuditingConfig;
import {{ base_package }}.common.exception.GlobalExceptionHandler;
import jakarta.persistence.Column;
import jakarta.persistence.EntityListeners;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.MappedSuperclass;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;
import lombok.Getter;
import lombok.Setter;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

/**
 * Shared JPA superclass giving every entity a consistent identity, audit trail, and
 * concurrency/soft-delete story, so individual entities don't have to redeclare this boilerplate:
 *
 * <ul>
 *   <li>a randomly generated UUID primary key ({@code id}),
 *   <li>automatic {@code created_at}/{@code updated_at} timestamps, populated by Spring Data's
 *       {@link AuditingEntityListener} (enabled via {@link JpaAuditingConfig}) rather than set by
 *       hand,
 *   <li>optimistic locking via {@code @Version}, so concurrent updates to the same row raise {@link
 *       org.springframework.orm.ObjectOptimisticLockingFailureException} instead of silently
 *       overwriting each other (handled centrally in {@link GlobalExceptionHandler}), and
 *   <li>a soft-delete convention via {@code deleted_at}.
 * </ul>
 *
 * <p><b>Important:</b> there is no global filter or Hibernate {@code @Where} clause that
 * automatically excludes soft-deleted rows from queries. Repositories for entities extending this
 * class must expose and use {@code *AndDeletedAtIsNull} query methods (see {@code
 * ExampleRepository}) wherever "not deleted" semantics are required; a plain {@code
 * findById}/{@code findAll} will return soft-deleted rows too.
 */
@Getter
@Setter
@MappedSuperclass
@EntityListeners(AuditingEntityListener.class)
public abstract class BaseEntity {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  @Column(name = "id", updatable = false, nullable = false)
  private UUID id;

  @CreatedDate
  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt;

  @LastModifiedDate
  @Column(name = "updated_at", nullable = false)
  private Instant updatedAt;

  @Version
  @Column(name = "version", nullable = false)
  private Long version;

  @Column(name = "deleted_at")
  private Instant deletedAt;

  /**
   * Indicates whether this entity has been soft-deleted.
   *
   * @return {@code true} if {@code deletedAt} is set, i.e. {@link #softDelete()} has been called
   *     and {@link #restore()} has not since been called
   */
  public boolean isDeleted() {
    return deletedAt != null;
  }

  /**
   * Marks this entity as deleted by stamping {@code deletedAt} with the current time, without
   * removing the row. Callers must persist the entity (e.g. via {@code repository.save(entity)})
   * for the change to take effect, and must query through a {@code *AndDeletedAtIsNull} repository
   * method afterward to exclude it from results, since no automatic filtering is applied.
   */
  public void softDelete() {
    this.deletedAt = Instant.now();
  }

  /**
   * Reverses a {@link #softDelete()} by clearing {@code deletedAt}. Callers must persist the entity
   * for the change to take effect.
   */
  public void restore() {
    this.deletedAt = null;
  }
}
