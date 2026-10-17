package {{ base_package }}.notification.dto;

import java.time.Instant;
import java.util.UUID;

/**
 * One entry of a recipient's in-app inbox.
 *
 * @param id the delivery id, used to mark the item read or dismiss it
 * @param notificationId the notification this item belongs to
 * @param type the trigger name the sender gave the notification
 * @param title the rendered title
 * @param body the rendered body
 * @param createdAt when the item was created
 * @param read whether the recipient has read it
 */
public record InboxItemResponse(
    UUID id,
    UUID notificationId,
    String type,
    String title,
    String body,
    Instant createdAt,
    boolean read) {}
