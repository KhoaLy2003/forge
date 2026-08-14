package {{ base_package }}.example.entity;

import {{ base_package }}.common.entity.BaseEntity;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Index;
import jakarta.persistence.Table;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/**
 * JPA entity backing the {@code example} table. This is the {@code entity} layer of the reference
 * six-package pattern: it owns persistence mapping only and extends {@code BaseEntity} for id,
 * audit timestamps ({@code createdAt}/{@code updatedAt}), optimistic-locking {@code version}, and
 * the {@code deletedAt} soft-delete marker. Indexes are declared on {@code status} and {@code
 * deleted_at} because both are used in the repository's filtered queries. When copying this package
 * for a new domain, rename the class/table, replace {@code name}/{@code status} with the new domain
 * fields, and revisit which columns actually need indexes.
 */
@Entity
@Table(
    name = "example",
    indexes = {
      @Index(name = "idx_example_status", columnList = "status"),
      @Index(name = "idx_example_deleted_at", columnList = "deleted_at")
    })
@Getter
@Setter
@NoArgsConstructor
public class Example extends BaseEntity {

  /** Display name; validated as required and length-limited at the DTO layer. */
  @Column(name = "name", nullable = false, length = 120)
  private String name;

  /** Lifecycle state, stored as its enum name; defaults to {@link ExampleStatus#ACTIVE}. */
  @Enumerated(EnumType.STRING)
  @Column(name = "status", nullable = false, length = 20)
  private ExampleStatus status = ExampleStatus.ACTIVE;

  /**
   * Constructs a new example, defaulting {@code status} to {@link ExampleStatus#ACTIVE} when {@code
   * null} is supplied (matching the field default for direct instantiation).
   *
   * @param name the example's display name
   * @param status initial status, or {@code null} to default to {@code ACTIVE}
   */
  @Builder
  public Example(String name, ExampleStatus status) {
    this.name = name;
    this.status = status != null ? status : ExampleStatus.ACTIVE;
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof Example other)) return false;
    return getId() != null && getId().equals(other.getId());
  }

  @Override
  public int hashCode() {
    return getClass().hashCode();
  }
}
