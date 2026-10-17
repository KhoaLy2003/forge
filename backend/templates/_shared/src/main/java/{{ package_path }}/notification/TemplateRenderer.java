package {{ base_package }}.notification;

import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Renders plain-text templates with double-brace placeholders such as {@code name} written between
 * two opening and two closing braces. A placeholder name matches {@code [a-zA-Z][a-zA-Z0-9]*}, with
 * optional spaces just inside the braces; anything else is left as ordinary text. Values are
 * inserted literally and are never themselves scanned for placeholders.
 */
public final class TemplateRenderer {

  private static final Pattern TOKEN = Pattern.compile("\\{\\{\\s*([a-zA-Z][a-zA-Z0-9]*)\\s*}}");

  private TemplateRenderer() {}

  /**
   * Replaces every placeholder with its value.
   *
   * @param text a template text
   * @param data placeholder values by name
   * @return the text with every placeholder replaced by its value; a missing value renders as an
   *     empty string
   */
  public static String render(String text, Map<String, String> data) {
    Matcher matcher = TOKEN.matcher(text);
    StringBuilder out = new StringBuilder();
    while (matcher.find()) {
      String value = data.get(matcher.group(1));
      matcher.appendReplacement(out, Matcher.quoteReplacement(value == null ? "" : value));
    }
    matcher.appendTail(out);
    return out.toString();
  }

  /**
   * Lists the placeholder names a template uses.
   *
   * @param text a template text
   * @return the distinct placeholder names in order of appearance
   */
  public static Set<String> placeholders(String text) {
    Set<String> names = new LinkedHashSet<>();
    Matcher matcher = TOKEN.matcher(text);
    while (matcher.find()) {
      names.add(matcher.group(1));
    }
    return names;
  }
}
