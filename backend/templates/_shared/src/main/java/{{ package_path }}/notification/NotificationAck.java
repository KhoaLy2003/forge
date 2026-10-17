package {{ base_package }}.notification;

import java.time.Instant;
import java.util.UUID;

/**
 * Acknowledgement that a notification was accepted into the outbox. Nothing has been sent yet:
 * delivery is asynchronous.
 *
 * @param id the notification id
 * @param status the notification status, see {@link NotificationStatus}
 * @param createdAt when the notification was created
 * @param duplicate {@code true} if the idempotency key already existed, in which case the other
 *     fields describe the original notification
 */
public record NotificationAck(UUID id, String status, Instant createdAt, boolean duplicate) {}
