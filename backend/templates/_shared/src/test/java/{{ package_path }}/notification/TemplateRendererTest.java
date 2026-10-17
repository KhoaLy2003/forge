package {{ base_package }}.notification;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Map;
import org.junit.jupiter.api.Test;

{% raw %}class TemplateRendererTest {

  @Test
  void render_replacesPlaceholdersAndToleratesInnerSpaces() {
    String out =
        TemplateRenderer.render(
            "In {{city}} and {{ city }}: {{name}}", Map.of("city", "Hanoi", "name", "Mia"));

    assertThat(out).isEqualTo("In Hanoi and Hanoi: Mia");
  }

  @Test
  void render_insertsValuesLiterally_evenWithRegexReplacementCharacters() {
    String out =
        TemplateRenderer.render("{{message}}", Map.of("message", "cost $1 and C:\\temp\\$2"));

    assertThat(out).isEqualTo("cost $1 and C:\\temp\\$2");
  }

  @Test
  void render_doesNotInterpretPlaceholdersInsideValues() {
    String out = TemplateRenderer.render("{{a}}", Map.of("a", "{{b}}", "b", "SECRET"));

    assertThat(out).isEqualTo("{{b}}");
  }

  @Test
  void render_withMissingValue_rendersEmptyString() {
    assertThat(TemplateRenderer.render("a{{missing}}b", Map.of())).isEqualTo("ab");
  }

  @Test
  void render_leavesTextWithoutPlaceholdersUntouched() {
    assertThat(TemplateRenderer.render("plain { text } here", Map.of()))
        .isEqualTo("plain { text } here");
  }

  @Test
  void render_ignoresMalformedPlaceholders() {
    assertThat(TemplateRenderer.render("{{ 1bad }} {{name", Map.of("name", "x")))
        .isEqualTo("{{ 1bad }} {{name");
  }

  @Test
  void placeholders_returnsDistinctNamesInOrder() {
    assertThat(TemplateRenderer.placeholders("{{b}} {{a}} {{b}} {{ c }}"))
        .containsExactly("b", "a", "c");
  }

  @Test
  void placeholders_ofTextWithoutPlaceholdersIsEmpty() {
    assertThat(TemplateRenderer.placeholders("nothing here")).isEmpty();
  }
}{% endraw %}
