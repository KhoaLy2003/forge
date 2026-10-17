package {{ base_package }}.notification;

import java.time.Instant;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/**
 * One send request handed to {@link NotificationService#enqueue}.
 *
 * @param type a trigger name such as {@code ORDER_SHIPPED}, stored for filtering and reporting
 * @param templateKey the template to render; it needs an active template for every channel
 * @param channels the channels to deliver on; never empty
 * @param audience the recipients
 * @param data template values; must cover every placeholder of the chosen templates
 * @param scheduledAt earliest delivery time, or {@code null} for immediately
 * @param idempotencyKey a key making repeated requests a no-op, or {@code null}
 * @param createdBy the acting user id, or {@code null} for system notifications
 */
public record NotificationRequest(
    String type,
    String templateKey,
    Set<NotificationChannel> channels,
    Audience audience,
    Map<String, String> data,
    Instant scheduledAt,
    String idempotencyKey,
    UUID createdBy) {}
