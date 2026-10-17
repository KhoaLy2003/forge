package {{ base_package }}.notification;

import {{ base_package }}.common.dto.PageResponse;
import {{ base_package }}.notification.dto.InboxItemResponse;
import {{ base_package }}.notification.dto.PreferencesResponse;
import {{ base_package }}.notification.dto.UpdatePreferencesRequest;
import java.util.UUID;

/**
 * The notification service: accepts send requests into the outbox and serves each recipient's inbox
 * and preferences. Delivery itself is done asynchronously by {@link DeliveryWorker}.
 */
public interface NotificationService {

  /**
   * Records a notification in the caller's transaction (REQUIRED, so it commits or rolls back with
   * the business change that caused it) and returns without sending anything. Deliveries are
   * created immediately for every recipient and channel.
   *
   * @param request the send request
   * @return the acknowledgement; {@code duplicate} is set when the idempotency key already existed
   * @throws IllegalArgumentException if a channel has no active template, template data is missing,
   *     or the audience is empty or larger than {@value
   *     NotificationServiceImpl#MAX_EXPLICIT_RECIPIENTS}
   */
  NotificationAck enqueue(NotificationRequest request);

  /**
   * Lists a recipient's in-app notifications.
   *
   * @param recipientId the recipient
   * @param page zero-based page index
   * @param size page size
   * @return the recipient's in-app notifications, newest first
   */
  PageResponse<InboxItemResponse> inbox(UUID recipientId, int page, int size);

  /**
   * Counts a recipient's unread in-app notifications.
   *
   * @param recipientId the recipient
   * @return the number of unread in-app notifications
   */
  long unreadCount(UUID recipientId);

  /**
   * Marks one in-app notification read.
   *
   * @param recipientId the recipient
   * @param deliveryId the in-app delivery id
   * @throws {{ base_package }}.common.exception.ResourceNotFoundException if it is unknown or
   *     not the recipient's
   */
  void markRead(UUID recipientId, UUID deliveryId);

  /**
   * Marks all of a recipient's in-app notifications read.
   *
   * @param recipientId the recipient
   */
  void markAllRead(UUID recipientId);

  /**
   * Removes one notification from the recipient's inbox.
   *
   * @param recipientId the recipient
   * @param deliveryId the in-app delivery id
   * @throws {{ base_package }}.common.exception.ResourceNotFoundException if it is unknown,
   *     already removed, or not the recipient's
   */
  void deleteNotification(UUID recipientId, UUID deliveryId);

  /**
   * Reads a recipient's preferences.
   *
   * @param recipientId the recipient
   * @return the stored preferences, or the defaults when none are stored
   */
  PreferencesResponse getPreferences(UUID recipientId);

  /**
   * Changes a recipient's preferences.
   *
   * @param recipientId the recipient
   * @param request the fields to change; {@code null} fields are kept
   * @return the resulting preferences
   */
  PreferencesResponse updatePreferences(UUID recipientId, UpdatePreferencesRequest request);

  /**
   * Deletes a recipient's deliveries and preferences (for example on account deletion).
   *
   * @param recipientId the recipient
   */
  void purgeRecipient(UUID recipientId);
}
