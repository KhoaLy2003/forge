package {{ base_package }}.notification.dto;

/**
 * A partial update of a recipient's notification preferences; a {@code null} field is left
 * unchanged.
 *
 * @param emailEnabled the new email switch, or {@code null} to keep the current value
 */
public record UpdatePreferencesRequest(Boolean emailEnabled) {}
