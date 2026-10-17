package {{ base_package }}.notification;

/**
 * What the notification module needs to know about a recipient beyond their id.
 *
 * @param email the address for the email channel
 * @param locale the two-letter locale used to pick a template, or {@code null} for the default
 */
public record Recipient(String email, String locale) {}
