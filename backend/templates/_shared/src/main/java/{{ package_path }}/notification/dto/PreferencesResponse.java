package {{ base_package }}.notification.dto;

/**
 * A recipient's notification preferences.
 *
 * @param emailEnabled whether email notifications are delivered
 */
public record PreferencesResponse(boolean emailEnabled) {}
