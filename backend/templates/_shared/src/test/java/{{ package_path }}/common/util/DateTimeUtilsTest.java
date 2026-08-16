package {{ base_package }}.common.util;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Locale;
import org.junit.jupiter.api.Test;

class DateTimeUtilsTest {

  private static final Instant FIXED_INSTANT = Instant.parse("2026-08-14T14:30:00Z");

  @Test
  void toIsoString_formatsInstantAsIso8601Utc() {
    String result = DateTimeUtils.toIsoString(FIXED_INSTANT);

    assertThat(result).isEqualTo("2026-08-14T14:30:00Z");
  }

  @Test
  void parseIsoString_parsesValueProducedByToIsoString() {
    Instant result = DateTimeUtils.parseIsoString("2026-08-14T14:30:00Z");

    assertThat(result).isEqualTo(FIXED_INSTANT);
  }

  @Test
  void parseIsoString_throwsIllegalArgumentExceptionOnMalformedInput() {
    assertThatThrownBy(() -> DateTimeUtils.parseIsoString("not-a-timestamp"))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("not-a-timestamp");
  }

  @Test
  void formatDate_formatsUtcDateOnly() {
    String result = DateTimeUtils.formatDate(FIXED_INSTANT);

    assertThat(result).isEqualTo("2026-08-14");
  }

  @Test
  void formatDateTime_formatsFixedHumanReadablePattern() {
    String result = DateTimeUtils.formatDateTime(FIXED_INSTANT);

    assertThat(result).isEqualTo("2026-08-14 14:30:00");
  }

  @Test
  void format_appliesCustomPatternAndZone() {
    String result = DateTimeUtils.format(FIXED_INSTANT, "dd/MM/yyyy HH:mm", ZoneOffset.UTC);

    assertThat(result).isEqualTo("14/08/2026 14:30");
  }

  @Test
  void formatForDisplay_rendersMediumStyleForUsLocale() {
    String result = DateTimeUtils.formatForDisplay(FIXED_INSTANT, Locale.US, ZoneOffset.UTC);

    // The JDK's CLDR locale data may render the space before AM/PM as a regular space or
    // a narrow no-break space (U+202F) depending on JDK version; normalize before asserting.
    String normalized = result.replace(' ', ' ');
    assertThat(normalized).isEqualTo("Aug 14, 2026, 2:30:00 PM");
  }

  @Test
  void humanizeDuration_returnsJustNowForInstantsWithinFiveSeconds() {
    Instant to = FIXED_INSTANT.plusSeconds(3);

    String result = DateTimeUtils.humanizeDuration(FIXED_INSTANT, to);

    assertThat(result).isEqualTo("just now");
  }

  @Test
  void humanizeDuration_returnsJustNowForIdenticalInstants() {
    String result = DateTimeUtils.humanizeDuration(FIXED_INSTANT, FIXED_INSTANT);

    assertThat(result).isEqualTo("just now");
  }

  @Test
  void humanizeDuration_pastSeconds_usesPluralWording() {
    Instant to = FIXED_INSTANT.plusSeconds(45);

    String result = DateTimeUtils.humanizeDuration(to, FIXED_INSTANT);

    assertThat(result).isEqualTo("45 seconds ago");
  }

  @Test
  void humanizeDuration_pastSingleMinute_usesSingularWording() {
    Instant to = FIXED_INSTANT.plusSeconds(60);

    String result = DateTimeUtils.humanizeDuration(to, FIXED_INSTANT);

    assertThat(result).isEqualTo("1 minute ago");
  }

  @Test
  void humanizeDuration_pastMultipleMinutes_usesPluralWording() {
    Instant to = FIXED_INSTANT.plusSeconds(3 * 60);

    String result = DateTimeUtils.humanizeDuration(to, FIXED_INSTANT);

    assertThat(result).isEqualTo("3 minutes ago");
  }

  @Test
  void humanizeDuration_pastHours_usesPluralWording() {
    Instant to = FIXED_INSTANT.plusSeconds(2 * 3600);

    String result = DateTimeUtils.humanizeDuration(to, FIXED_INSTANT);

    assertThat(result).isEqualTo("2 hours ago");
  }

  @Test
  void humanizeDuration_pastDays_usesPluralWording() {
    Instant to = FIXED_INSTANT.plusSeconds(2L * 24 * 3600);

    String result = DateTimeUtils.humanizeDuration(to, FIXED_INSTANT);

    assertThat(result).isEqualTo("2 days ago");
  }

  @Test
  void humanizeDuration_futureMinutes_usesInPrefix() {
    Instant to = FIXED_INSTANT.plusSeconds(5 * 60);

    String result = DateTimeUtils.humanizeDuration(FIXED_INSTANT, to);

    assertThat(result).isEqualTo("in 5 minutes");
  }

  @Test
  void humanizeDuration_futureSingleHour_usesSingularWording() {
    Instant to = FIXED_INSTANT.plusSeconds(3600);

    String result = DateTimeUtils.humanizeDuration(FIXED_INSTANT, to);

    assertThat(result).isEqualTo("in 1 hour");
  }

  @Test
  void humanizeDuration_futureDays_usesPluralWording() {
    Instant to = FIXED_INSTANT.plusSeconds(3L * 24 * 3600);

    String result = DateTimeUtils.humanizeDuration(FIXED_INSTANT, to);

    assertThat(result).isEqualTo("in 3 days");
  }
}
