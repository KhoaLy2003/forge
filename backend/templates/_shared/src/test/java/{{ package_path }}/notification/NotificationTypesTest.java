package {{ base_package }}.notification;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.HashSet;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class NotificationTypesTest {

  @Test
  void channel_dbValuesMatchTheMigrationCheckConstraint() {
    assertThat(NotificationChannel.IN_APP.dbValue()).isEqualTo("in_app");
    assertThat(NotificationChannel.EMAIL.dbValue()).isEqualTo("email");
    assertThat(NotificationChannel.values()).hasSize(2);
  }

  @Test
  void channel_fromDbRoundTripsEveryChannel() {
    for (NotificationChannel channel : NotificationChannel.values()) {
      assertThat(NotificationChannel.fromDb(channel.dbValue())).isEqualTo(channel);
    }
  }

  @Test
  void channel_fromDbRejectsUnknownValues() {
    assertThatThrownBy(() -> NotificationChannel.fromDb("push"))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("push");
    assertThatThrownBy(() -> NotificationChannel.fromDb(null))
        .isInstanceOf(IllegalArgumentException.class);
  }

  @Test
  void audience_usersCopiesTheIdsSoLaterChangesDoNotLeakIn() {
    UUID first = UUID.randomUUID();
    Set<UUID> ids = new HashSet<>(Set.of(first));

    Audience audience = Audience.users(ids);
    ids.add(UUID.randomUUID());

    assertThat(audience.type()).isEqualTo(Audience.USERS);
    assertThat(audience.userIds()).containsExactly(first);
  }

  @Test
  void audience_userIdsAreUnmodifiable() {
    Audience audience = Audience.users(Set.of(UUID.randomUUID()));

    assertThatThrownBy(() -> audience.userIds().add(UUID.randomUUID()))
        .isInstanceOf(UnsupportedOperationException.class);
  }

  @Test
  void deliverySkipReasonsFitTheSkipReasonColumn() {
    for (String reason :
        new String[] {
          DeliveryStatus.SKIP_OPTED_OUT,
          DeliveryStatus.SKIP_NO_TEMPLATE,
          DeliveryStatus.SKIP_EMAIL_NOT_CONFIGURED,
          DeliveryStatus.SKIP_RECIPIENT_UNRESOLVED,
          DeliveryStatus.SKIP_CANCELLED
        }) {
      assertThat(reason).isNotBlank().hasSizeLessThanOrEqualTo(30);
    }
  }

  @Test
  void statusConstantsMatchTheStoredStrings() {
    assertThat(DeliveryStatus.PENDING).isEqualTo("pending");
    assertThat(DeliveryStatus.SENT).isEqualTo("sent");
    assertThat(DeliveryStatus.FAILED).isEqualTo("failed");
    assertThat(DeliveryStatus.SKIPPED).isEqualTo("skipped");
    assertThat(NotificationStatus.ACCEPTED).isEqualTo("accepted");
    assertThat(NotificationStatus.QUEUED).isEqualTo("queued");
    assertThat(NotificationStatus.COMPLETED).isEqualTo("completed");
    assertThat(NotificationStatus.PARTIALLY_FAILED).isEqualTo("partially_failed");
    assertThat(NotificationStatus.FAILED).isEqualTo("failed");
    assertThat(NotificationStatus.CANCELLED).isEqualTo("cancelled");
  }
}
