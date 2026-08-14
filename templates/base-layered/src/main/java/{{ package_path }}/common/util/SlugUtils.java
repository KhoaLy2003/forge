package {{ base_package }}.common.util;

import java.text.Normalizer;
import java.util.regex.Pattern;

/**
 * Static helpers for turning human-readable strings into URL-safe slugs and for bounding string
 * length for display or storage purposes. Not instantiable.
 */
public final class SlugUtils {

  private static final Pattern COMBINING_MARKS = Pattern.compile("\\p{M}+");
  private static final Pattern NON_ALPHANUMERIC_RUN = Pattern.compile("[^a-z0-9]+");
  private static final Pattern LEADING_TRAILING_HYPHENS = Pattern.compile("^-+|-+$");

  private SlugUtils() {}

  /**
   * Converts a human-readable string into a lowercase, URL-safe slug.
   *
   * <p>Diacritics/accents are stripped (e.g. {@code "é"} becomes {@code "e"}), and any run of one
   * or more characters that are not lowercase letters or digits is collapsed into a single hyphen.
   * Leading and trailing hyphens are trimmed from the result.
   *
   * @param input the human-readable string to slugify
   * @return the resulting slug, e.g. {@code "My Awesome Widget!"} becomes {@code
   *     "my-awesome-widget"}
   * @throws IllegalArgumentException if {@code input} is {@code null} or blank
   */
  public static String slugify(String input) {
    if (input == null || input.isBlank()) {
      throw new IllegalArgumentException(
          "input must not be null or blank; a slug from nothing is meaningless");
    }
    String normalized = Normalizer.normalize(input, Normalizer.Form.NFD);
    String withoutDiacritics = COMBINING_MARKS.matcher(normalized).replaceAll("");
    String lowercased = withoutDiacritics.toLowerCase();
    String hyphenated = NON_ALPHANUMERIC_RUN.matcher(lowercased).replaceAll("-");
    return LEADING_TRAILING_HYPHENS.matcher(hyphenated).replaceAll("");
  }

  /**
   * Truncates {@code input} to at most {@code maxLength} characters.
   *
   * @param input the string to truncate; may be {@code null}
   * @param maxLength the maximum number of characters to retain
   * @return {@code null} if {@code input} is {@code null}; otherwise {@code input} unchanged if its
   *     length is less than or equal to {@code maxLength}, or the first {@code maxLength}
   *     characters of {@code input} otherwise
   * @throws IllegalArgumentException if {@code maxLength} is negative
   */
  public static String truncate(String input, int maxLength) {
    if (maxLength < 0) {
      throw new IllegalArgumentException("maxLength must not be negative: " + maxLength);
    }
    if (input == null) {
      return null;
    }
    if (input.length() <= maxLength) {
      return input;
    }
    return input.substring(0, maxLength);
  }
}
