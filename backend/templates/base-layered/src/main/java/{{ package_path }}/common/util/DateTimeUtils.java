package {{ base_package }}.common.util;

import java.time.Duration;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.time.format.FormatStyle;
import java.util.Locale;

/**
 * Static helpers for converting between {@link Instant} and the various textual representations
 * used across the API: wire-format ISO-8601 timestamps, fixed human-readable date/date-time
 * strings, locale-aware display strings, and relative "time ago" phrasing. Not instantiable.
 */
public final class DateTimeUtils {

  private static final DateTimeFormatter DATE_TIME_PATTERN =
      DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss").withZone(ZoneOffset.UTC);

  private DateTimeUtils() {}

  /**
   * Formats an {@link Instant} as an ISO-8601 UTC string, e.g. {@code 2026-08-14T14:30:00Z}.
   *
   * @param instant the instant to format
   * @return the ISO-8601 UTC representation of {@code instant}
   */
  public static String toIsoString(Instant instant) {
    return DateTimeFormatter.ISO_INSTANT.format(instant);
  }

  /**
   * Parses an ISO-8601 UTC string produced by {@link #toIsoString(Instant)} back into an {@link
   * Instant}.
   *
   * @param value the ISO-8601 string to parse, e.g. {@code 2026-08-14T14:30:00Z}
   * @return the parsed {@link Instant}
   * @throws IllegalArgumentException if {@code value} is not a well-formed ISO-8601 instant
   */
  public static Instant parseIsoString(String value) {
    try {
      return Instant.parse(value);
    } catch (DateTimeParseException e) {
      throw new IllegalArgumentException("Malformed ISO-8601 instant: '" + value + "'", e);
    }
  }

  /**
   * Formats an {@link Instant} as a UTC date-only ISO string, e.g. {@code 2026-08-14}.
   *
   * @param instant the instant to format
   * @return the UTC date portion of {@code instant} in ISO-8601 format
   */
  public static String formatDate(Instant instant) {
    LocalDate date = LocalDate.ofInstant(instant, ZoneOffset.UTC);
    return DateTimeFormatter.ISO_LOCAL_DATE.format(date);
  }

  /**
   * Formats an {@link Instant} as a fixed human-readable UTC date-time string using the pattern
   * {@code yyyy-MM-dd HH:mm:ss}, e.g. {@code 2026-08-14 14:30:00}. This is distinct from {@link
   * #toIsoString(Instant)}, which produces the ISO-8601 wire format.
   *
   * @param instant the instant to format
   * @return {@code instant} formatted as {@code yyyy-MM-dd HH:mm:ss} in UTC
   */
  public static String formatDateTime(Instant instant) {
    return DATE_TIME_PATTERN.format(instant);
  }

  /**
   * General-purpose formatter for callers whose desired output isn't covered by the fixed helpers
   * in this class.
   *
   * @param instant the instant to format
   * @param pattern a {@link DateTimeFormatter} pattern, e.g. {@code "dd/MM/yyyy"}
   * @param zone the zone to render {@code instant} in
   * @return {@code instant} formatted according to {@code pattern} in {@code zone}
   * @throws IllegalArgumentException if {@code pattern} is not a valid formatter pattern
   */
  public static String format(Instant instant, String pattern, ZoneId zone) {
    return DateTimeFormatter.ofPattern(pattern).format(instant.atZone(zone));
  }

  /**
   * Formats an {@link Instant} for locale-aware human display, e.g. {@code "Aug 14, 2026, 2:30:00
   * PM"} for {@link Locale#US}, using {@link FormatStyle#MEDIUM} date and time styles.
   *
   * @param instant the instant to format
   * @param locale the locale to render the display string in
   * @param zone the zone to render {@code instant} in
   * @return a locale-aware, medium-style display string for {@code instant}
   */
  public static String formatForDisplay(Instant instant, Locale locale, ZoneId zone) {
    return DateTimeFormatter.ofLocalizedDateTime(FormatStyle.MEDIUM)
        .withLocale(locale)
        .format(instant.atZone(zone));
  }

  /**
   * Produces a short relative-time phrase describing the gap between two instants, e.g. {@code "3
   * minutes ago"}, {@code "in 2 hours"}, or {@code "just now"}.
   *
   * <p>Durations of five seconds or less in either direction are reported as {@code "just now"}.
   * Otherwise the gap is bucketed into the largest whole unit it fits (seconds, minutes, hours, or
   * days) with correct singular/plural wording, and rendered as {@code "<n> <unit>(s) ago"} when
   * {@code to} is before {@code from}, or {@code "in <n> <unit>(s)"} when {@code to} is after
   * {@code from}.
   *
   * @param from the reference instant
   * @param to the instant being described relative to {@code from}
   * @return a short human-readable phrase describing the gap between {@code from} and {@code to}
   */
  public static String humanizeDuration(Instant from, Instant to) {
    Duration duration = Duration.between(from, to);
    boolean isFuture = duration.isNegative() == false && duration.isZero() == false;
    Duration absolute = duration.abs();

    if (absolute.getSeconds() <= 5) {
      return "just now";
    }

    long amount;
    String unit;
    if (absolute.toSeconds() < 60) {
      amount = absolute.toSeconds();
      unit = "second";
    } else if (absolute.toMinutes() < 60) {
      amount = absolute.toMinutes();
      unit = "minute";
    } else if (absolute.toHours() < 24) {
      amount = absolute.toHours();
      unit = "hour";
    } else {
      amount = absolute.toDays();
      unit = "day";
    }

    String plural = amount == 1 ? unit : unit + "s";
    return isFuture ? "in " + amount + " " + plural : amount + " " + plural + " ago";
  }
}
