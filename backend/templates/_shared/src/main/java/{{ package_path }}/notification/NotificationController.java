package {{ base_package }}.notification;

import {{ base_package }}.common.dto.ApiResponse;
import {{ base_package }}.common.dto.PageResponse;
import {{ base_package }}.common.exception.UnauthorizedException;
import {{ base_package }}.notification.dto.InboxItemResponse;
import {{ base_package }}.notification.dto.PreferencesResponse;
import {{ base_package }}.notification.dto.UnreadCountResponse;
import {{ base_package }}.notification.dto.UpdatePreferencesRequest;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * REST entry point for the caller's own notifications under {@code /api/v1/notifications}: inbox,
 * unread count, read markers and preferences. The caller is whoever the project's {@link
 * CurrentRecipientProvider} says it is; without one every route answers {@code 401}. No route takes
 * a recipient id from the client, and none creates notifications - other code does that through
 * {@link NotificationService#enqueue}.
 */
@RestController
@RequestMapping("/api/v1/notifications")
@RequiredArgsConstructor
@Tag(name = "Notifications", description = "Inbox and notification preferences")
@Validated
public class NotificationController {

  private final NotificationService service;
  private final ObjectProvider<CurrentRecipientProvider> currentRecipient;

  private UUID caller() {
    return currentRecipient
        .getIfAvailable(() -> CurrentRecipientProvider.NONE)
        .currentRecipientId()
        .orElseThrow(() -> new UnauthorizedException("Authentication required"));
  }

  /**
   * {@code GET /api/v1/notifications} - the caller's in-app notifications, newest first.
   *
   * @param page zero-based page index (default {@code 0})
   * @param size page size, 1-100 (default {@code 20})
   * @return {@code 200 OK} with a page of inbox items
   */
  @GetMapping
  @Operation(summary = "List my notifications")
  public ResponseEntity<ApiResponse<PageResponse<InboxItemResponse>>> list(
      @RequestParam(defaultValue = "0") @Min(0) int page,
      @RequestParam(defaultValue = "20") @Min(1) @Max(100) int size) {
    UUID recipient = caller();
    return ResponseEntity.ok(
        ApiResponse.success(
            "Notifications retrieved successfully", service.inbox(recipient, page, size)));
  }

  /**
   * {@code GET /api/v1/notifications/unread-count} - how many notifications are unread.
   *
   * @return {@code 200 OK} with the count
   */
  @GetMapping("/unread-count")
  @Operation(summary = "Count my unread notifications")
  public ResponseEntity<ApiResponse<UnreadCountResponse>> unreadCount() {
    UUID recipient = caller();
    return ResponseEntity.ok(
        ApiResponse.success(
            "Unread count retrieved successfully",
            new UnreadCountResponse(service.unreadCount(recipient))));
  }

  /**
   * {@code PATCH /api/v1/notifications/{id}/read} - marks one notification read.
   *
   * @param id the delivery id from the inbox
   * @return {@code 204 No Content}; {@code 404} if it is not one of the caller's notifications
   */
  @PatchMapping("/{id}/read")
  @Operation(summary = "Mark a notification as read")
  public ResponseEntity<Void> markRead(@PathVariable UUID id) {
    service.markRead(caller(), id);
    return ResponseEntity.noContent().build();
  }

  /**
   * {@code POST /api/v1/notifications/read-all} - marks every notification read.
   *
   * @return {@code 204 No Content}
   */
  @PostMapping("/read-all")
  @Operation(summary = "Mark all notifications as read")
  public ResponseEntity<Void> markAllRead() {
    service.markAllRead(caller());
    return ResponseEntity.noContent().build();
  }

  /**
   * {@code DELETE /api/v1/notifications/{id}} - removes a notification from the caller's inbox.
   *
   * @param id the delivery id from the inbox
   * @return {@code 204 No Content}; {@code 404} if it is not one of the caller's notifications
   */
  @DeleteMapping("/{id}")
  @Operation(summary = "Delete a notification from my inbox")
  public ResponseEntity<Void> delete(@PathVariable UUID id) {
    service.deleteNotification(caller(), id);
    return ResponseEntity.noContent().build();
  }

  /**
   * {@code GET /api/v1/notifications/preferences} - the caller's notification preferences.
   *
   * @return {@code 200 OK} with the preferences (defaults if none are stored)
   */
  @GetMapping("/preferences")
  @Operation(summary = "Get my notification preferences")
  public ResponseEntity<ApiResponse<PreferencesResponse>> getPreferences() {
    UUID recipient = caller();
    return ResponseEntity.ok(
        ApiResponse.success(
            "Preferences retrieved successfully", service.getPreferences(recipient)));
  }

  /**
   * {@code PUT /api/v1/notifications/preferences} - changes the caller's preferences; omitted
   * fields keep their value.
   *
   * @param request the fields to change
   * @return {@code 200 OK} with the resulting preferences
   */
  @PutMapping("/preferences")
  @Operation(summary = "Update my notification preferences")
  public ResponseEntity<ApiResponse<PreferencesResponse>> updatePreferences(
      @Valid @RequestBody UpdatePreferencesRequest request) {
    UUID recipient = caller();
    return ResponseEntity.ok(
        ApiResponse.success(
            "Preferences updated successfully", service.updatePreferences(recipient, request)));
  }
}
