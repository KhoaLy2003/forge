package {{ base_package }}.common.util;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;

import org.junit.jupiter.api.Test;

class SlugUtilsTest {

  @Test
  void slugify_lowercasesAndHyphenatesPunctuationAndSpaces() {
    String result = SlugUtils.slugify("My Awesome Widget!");

    assertThat(result).isEqualTo("my-awesome-widget");
  }

  @Test
  void slugify_stripsDiacriticsAndCollapsesMultipleSeparators() {
    String result = SlugUtils.slugify("Café  Münchën");

    assertThat(result).isEqualTo("cafe-munchen");
  }

  @Test
  void slugify_trimsLeadingAndTrailingHyphens() {
    String result = SlugUtils.slugify("  ***Hello World***  ");

    assertThat(result).isEqualTo("hello-world");
  }

  @Test
  void slugify_throwsOnNullInput() {
    assertThatIllegalArgumentException().isThrownBy(() -> SlugUtils.slugify(null));
  }

  @Test
  void slugify_throwsOnBlankInput() {
    assertThatIllegalArgumentException().isThrownBy(() -> SlugUtils.slugify("   "));
  }

  @Test
  void truncate_returnsInputUnchangedWhenBelowLimit() {
    String result = SlugUtils.truncate("hello", 10);

    assertThat(result).isEqualTo("hello");
  }

  @Test
  void truncate_returnsInputUnchangedWhenExactlyAtLimit() {
    String result = SlugUtils.truncate("hello", 5);

    assertThat(result).isEqualTo("hello");
  }

  @Test
  void truncate_cutsInputWhenAboveLimit() {
    String result = SlugUtils.truncate("hello world", 5);

    assertThat(result).isEqualTo("hello");
  }

  @Test
  void truncate_returnsEmptyStringWhenMaxLengthIsZero() {
    String result = SlugUtils.truncate("hello", 0);

    assertThat(result).isEmpty();
  }

  @Test
  void truncate_throwsOnNegativeMaxLength() {
    assertThatIllegalArgumentException().isThrownBy(() -> SlugUtils.truncate("hello", -1));
  }

  @Test
  void truncate_returnsNullForNullInput() {
    String result = SlugUtils.truncate(null, 5);

    assertThat(result).isNull();
  }
}
