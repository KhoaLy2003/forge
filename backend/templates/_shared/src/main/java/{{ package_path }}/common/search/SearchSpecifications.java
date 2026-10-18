package {{ base_package }}.common.search;

import java.util.Locale;
import java.util.UUID;
import org.springframework.data.jpa.domain.Specification;

/**
 * Building blocks for the generated {@code <Entity>Filter} records: each method turns one optional
 * query parameter into a JPA {@link Specification}, or {@code null} when the parameter was not
 * supplied, so {@link #notDeletedAnd} can skip it.
 *
 * <p>Attribute names are never taken from a request. The generated filters pass literal attribute
 * names, so a client can only filter on the fields the entity model declares. Every search starts
 * from {@link #notDeleted()}, which keeps soft-deleted rows out just like the {@code
 * *AndDeletedAtIsNull} repository finders.
 */
public final class SearchSpecifications {

  private static final char ESCAPE = '\\';

  private SearchSpecifications() {}

  /**
   * Matches rows that have not been soft-deleted.
   *
   * @param <T> the entity type
   * @return a specification on {@code deletedAt IS NULL}
   */
  public static <T> Specification<T> notDeleted() {
    return (root, query, builder) -> builder.isNull(root.get("deletedAt"));
  }

  /**
   * Combines {@link #notDeleted()} with every non-null filter using AND.
   *
   * @param filters the optional filter specifications; {@code null} entries are ignored
   * @param <T> the entity type
   * @return the combined specification
   */
  @SafeVarargs
  public static <T> Specification<T> notDeletedAnd(Specification<T>... filters) {
    Specification<T> result = notDeleted();
    for (Specification<T> filter : filters) {
      if (filter != null) {
        result = result.and(filter);
      }
    }
    return result;
  }

  /**
   * Case-insensitive substring match. {@code %}, {@code _} and the escape character in {@code
   * value} are matched literally, not as wildcards.
   *
   * @param attribute the string attribute of the entity
   * @param value the text to look for; {@code null} or blank means no filter
   * @param <T> the entity type
   * @return the specification, or {@code null} when there is nothing to filter on
   */
  public static <T> Specification<T> contains(String attribute, String value) {
    if (value == null || value.isBlank()) {
      return null;
    }
    String pattern = "%" + escapeLike(value.toLowerCase(Locale.ROOT)) + "%";
    return (root, query, builder) ->
        builder.like(builder.lower(root.<String>get(attribute)), pattern, ESCAPE);
  }

  /**
   * Exact match.
   *
   * @param attribute the attribute of the entity
   * @param value the required value; {@code null} means no filter
   * @param <T> the entity type
   * @return the specification, or {@code null} when there is nothing to filter on
   */
  public static <T> Specification<T> equal(String attribute, Object value) {
    if (value == null) {
      return null;
    }
    return (root, query, builder) -> builder.equal(root.get(attribute), value);
  }

  /**
   * Inclusive lower bound.
   *
   * @param attribute the comparable attribute of the entity
   * @param value the smallest accepted value; {@code null} means no filter
   * @param <T> the entity type
   * @param <V> the attribute type
   * @return the specification, or {@code null} when there is nothing to filter on
   */
  public static <T, V extends Comparable<? super V>> Specification<T> atLeast(
      String attribute, V value) {
    if (value == null) {
      return null;
    }
    return (root, query, builder) -> builder.greaterThanOrEqualTo(root.<V>get(attribute), value);
  }

  /**
   * Inclusive upper bound.
   *
   * @param attribute the comparable attribute of the entity
   * @param value the largest accepted value; {@code null} means no filter
   * @param <T> the entity type
   * @param <V> the attribute type
   * @return the specification, or {@code null} when there is nothing to filter on
   */
  public static <T, V extends Comparable<? super V>> Specification<T> atMost(
      String attribute, V value) {
    if (value == null) {
      return null;
    }
    return (root, query, builder) -> builder.lessThanOrEqualTo(root.<V>get(attribute), value);
  }

  /**
   * Matches rows whose to-one association points at the given id. Compares the foreign key column;
   * the related row is not loaded or joined.
   *
   * @param association the to-one association attribute of the entity
   * @param id the related entity's id; {@code null} means no filter
   * @param <T> the entity type
   * @return the specification, or {@code null} when there is nothing to filter on
   */
  public static <T> Specification<T> idEquals(String association, UUID id) {
    if (id == null) {
      return null;
    }
    return (root, query, builder) -> builder.equal(root.get(association).get("id"), id);
  }

  private static String escapeLike(String value) {
    return value
        .replace(String.valueOf(ESCAPE), ESCAPE + String.valueOf(ESCAPE))
        .replace("%", ESCAPE + "%")
        .replace("_", ESCAPE + "_");
  }
}
