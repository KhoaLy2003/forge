package {{ base_package }}.example.entity;

/**
 * Lifecycle states for {@link Example}, stored by name via {@code @Enumerated(EnumType.STRING)}.
 * This is distinct from soft-delete (see {@code BaseEntity#deletedAt}): {@code ARCHIVED} examples
 * are still live, queryable records that a user has deactivated, whereas a deleted example is
 * excluded from queries entirely. When copying this package for a new domain, replace with whatever
 * states that resource's lifecycle actually needs.
 */
public enum ExampleStatus {
  /** Default state for newly created and actively used examples. */
  ACTIVE,
  /** Deactivated but not deleted; still retrievable and still unique-name-checked. */
  ARCHIVED
}
