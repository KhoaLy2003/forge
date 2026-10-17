package {{ base_package }}.notification.dto;

/**
 * The number of unread notifications in a recipient's inbox.
 *
 * @param count the number of unread, visible in-app notifications
 */
public record UnreadCountResponse(long count) {}
