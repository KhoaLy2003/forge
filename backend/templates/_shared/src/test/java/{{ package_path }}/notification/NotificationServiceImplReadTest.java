package {{ base_package }}.notification;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import {{ base_package }}.common.dto.PageResponse;
import {{ base_package }}.common.exception.ResourceNotFoundException;
import {{ base_package }}.notification.dto.InboxItemResponse;
import {{ base_package }}.notification.dto.PreferencesResponse;
import {{ base_package }}.notification.dto.UpdatePreferencesRequest;
import {{ base_package }}.notification.entity.NotificationPreference;
import {{ base_package }}.notification.repository.NotificationPreferenceRepository;
import {{ base_package }}.notification.repository.NotificationTemplateRepository;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

class NotificationServiceImplReadTest {

  private final NotificationQueries queries = mock(NotificationQueries.class);
  private final NotificationPreferenceRepository preferences =
      mock(NotificationPreferenceRepository.class);
  private final NotificationServiceImpl service =
      new NotificationServiceImpl(queries, mock(NotificationTemplateRepository.class), preferences);

  private final UUID recipient = UUID.randomUUID();

  private static NotificationQueries.InboxRow row(String title, boolean read) {
    return new NotificationQueries.InboxRow(
        UUID.randomUUID(),
        UUID.randomUUID(),
        "WELCOME",
        title,
        "body of " + title,
        Instant.parse("2026-01-01T00:00:00Z"),
        read);
  }

  // -------------------------------------------------------------------- inbox

  @Test
  void inbox_mapsRowsAndDerivesPaginationFromTheTotal() {
    NotificationQueries.InboxRow first = row("one", false);
    NotificationQueries.InboxRow second = row("two", true);
    when(queries.inbox(recipient, 2, 2L)).thenReturn(List.of(first, second));
    when(queries.inboxCount(recipient)).thenReturn(5L);

    PageResponse<InboxItemResponse> page = service.inbox(recipient, 1, 2);

    assertThat(page.getData())
        .containsExactly(
            new InboxItemResponse(
                first.id(),
                first.notificationId(),
                "WELCOME",
                "one",
                "body of one",
                first.createdAt(),
                false),
            new InboxItemResponse(
                second.id(),
                second.notificationId(),
                "WELCOME",
                "two",
                "body of two",
                second.createdAt(),
                true));
    assertThat(page.getPagination().getPage()).isEqualTo(1);
    assertThat(page.getPagination().getLimit()).isEqualTo(2);
    assertThat(page.getPagination().getTotal()).isEqualTo(5);
    assertThat(page.getPagination().getTotalPages()).isEqualTo(3);
    assertThat(page.getPagination().isHasNext()).isTrue();
    assertThat(page.getPagination().isHasPrev()).isTrue();
  }

  @Test
  void inbox_ofAnEmptyInbox_isAnEmptyPage() {
    when(queries.inbox(recipient, 20, 0L)).thenReturn(List.of());
    when(queries.inboxCount(recipient)).thenReturn(0L);

    PageResponse<InboxItemResponse> page = service.inbox(recipient, 0, 20);

    assertThat(page.getData()).isEmpty();
    assertThat(page.getPagination().getTotal()).isZero();
    assertThat(page.getPagination().isHasNext()).isFalse();
    assertThat(page.getPagination().isHasPrev()).isFalse();
  }

  @Test
  void inbox_pastTheLastPage_isEmptyButKeepsTheTotal() {
    when(queries.inbox(recipient, 10, 50L)).thenReturn(List.of());
    when(queries.inboxCount(recipient)).thenReturn(3L);

    PageResponse<InboxItemResponse> page = service.inbox(recipient, 5, 10);

    assertThat(page.getData()).isEmpty();
    assertThat(page.getPagination().getTotal()).isEqualTo(3);
    assertThat(page.getPagination().isHasNext()).isFalse();
  }

  @Test
  void inbox_onlyEverQueriesForTheGivenRecipient() {
    when(queries.inbox(
            any(), org.mockito.ArgumentMatchers.anyInt(), org.mockito.ArgumentMatchers.anyLong()))
        .thenReturn(List.of());

    service.inbox(recipient, 0, 20);

    verify(queries).inbox(recipient, 20, 0L);
    verify(queries).inboxCount(recipient);
  }

  @Test
  void unreadCount_delegatesToTheQueries() {
    when(queries.unreadCount(recipient)).thenReturn(7L);

    assertThat(service.unreadCount(recipient)).isEqualTo(7);
  }

  // ---------------------------------------------------------- read / dismiss

  @Test
  void markRead_forAnUnknownOrForeignDelivery_isNotFound() {
    UUID delivery = UUID.randomUUID();
    when(queries.markRead(delivery, recipient)).thenReturn(false);

    assertThatThrownBy(() -> service.markRead(recipient, delivery))
        .isInstanceOf(ResourceNotFoundException.class)
        .hasMessageContaining(delivery.toString());
  }

  @Test
  void markRead_forTheRecipientsOwnDelivery_succeeds() {
    UUID delivery = UUID.randomUUID();
    when(queries.markRead(delivery, recipient)).thenReturn(true);

    service.markRead(recipient, delivery);

    verify(queries).markRead(delivery, recipient);
  }

  @Test
  void markAllRead_delegatesForTheRecipient() {
    service.markAllRead(recipient);

    verify(queries).markAllRead(recipient);
  }

  @Test
  void deleteNotification_forAnUnknownOrForeignOrAlreadyDismissedDelivery_isNotFound() {
    UUID delivery = UUID.randomUUID();
    when(queries.dismiss(delivery, recipient)).thenReturn(false);

    assertThatThrownBy(() -> service.deleteNotification(recipient, delivery))
        .isInstanceOf(ResourceNotFoundException.class);
  }

  @Test
  void deleteNotification_forTheRecipientsOwnDelivery_succeeds() {
    UUID delivery = UUID.randomUUID();
    when(queries.dismiss(delivery, recipient)).thenReturn(true);

    service.deleteNotification(recipient, delivery);

    verify(queries).dismiss(delivery, recipient);
  }

  // -------------------------------------------------------------- preferences

  @Test
  void getPreferences_withoutAStoredRow_returnsTheDefaults() {
    when(preferences.findByRecipientIdAndDeletedAtIsNull(recipient)).thenReturn(Optional.empty());

    assertThat(service.getPreferences(recipient)).isEqualTo(new PreferencesResponse(true));
  }

  @Test
  void getPreferences_withAStoredRow_returnsIt() {
    NotificationPreference stored = NotificationPreference.builder().recipientId(recipient).build();
    stored.setEmailEnabled(false);
    when(preferences.findByRecipientIdAndDeletedAtIsNull(recipient))
        .thenReturn(Optional.of(stored));

    assertThat(service.getPreferences(recipient)).isEqualTo(new PreferencesResponse(false));
  }

  @Test
  void updatePreferences_createsTheRowWhenMissingAndAppliesTheChange() {
    when(preferences.findByRecipientIdAndDeletedAtIsNull(recipient)).thenReturn(Optional.empty());
    when(preferences.save(any(NotificationPreference.class)))
        .thenAnswer(call -> call.getArgument(0));

    PreferencesResponse response =
        service.updatePreferences(recipient, new UpdatePreferencesRequest(false));

    ArgumentCaptor<NotificationPreference> saved =
        ArgumentCaptor.forClass(NotificationPreference.class);
    verify(preferences).save(saved.capture());
    assertThat(saved.getValue().getRecipientId()).isEqualTo(recipient);
    assertThat(saved.getValue().isEmailEnabled()).isFalse();
    assertThat(response).isEqualTo(new PreferencesResponse(false));
  }

  @Test
  void updatePreferences_withANullField_leavesTheStoredValueUntouched() {
    NotificationPreference stored = NotificationPreference.builder().recipientId(recipient).build();
    stored.setEmailEnabled(false);
    when(preferences.findByRecipientIdAndDeletedAtIsNull(recipient))
        .thenReturn(Optional.of(stored));
    when(preferences.save(any(NotificationPreference.class)))
        .thenAnswer(call -> call.getArgument(0));

    PreferencesResponse response =
        service.updatePreferences(recipient, new UpdatePreferencesRequest(null));

    assertThat(response).isEqualTo(new PreferencesResponse(false));
    assertThat(stored.isEmailEnabled()).isFalse();
  }

  @Test
  void updatePreferences_canTurnEmailBackOn() {
    NotificationPreference stored = NotificationPreference.builder().recipientId(recipient).build();
    stored.setEmailEnabled(false);
    when(preferences.findByRecipientIdAndDeletedAtIsNull(recipient))
        .thenReturn(Optional.of(stored));
    when(preferences.save(any(NotificationPreference.class)))
        .thenAnswer(call -> call.getArgument(0));

    PreferencesResponse response =
        service.updatePreferences(recipient, new UpdatePreferencesRequest(true));

    assertThat(response.emailEnabled()).isTrue();
  }

  // -------------------------------------------------------------------- purge

  @Test
  void purgeRecipient_removesDeliveriesAndPreferencesOfThatRecipientOnly() {
    service.purgeRecipient(recipient);

    verify(queries).deleteDeliveriesOf(recipient);
    verify(preferences).deleteByRecipientId(recipient);
    verify(queries, never())
        .deleteDeliveriesOf(org.mockito.ArgumentMatchers.argThat(id -> !id.equals(recipient)));
  }
}
