package {{ base_package }}.notification;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.jdbc.test.autoconfigure.AutoConfigureTestDatabase;
import org.springframework.boot.jdbc.test.autoconfigure.JdbcTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import tools.jackson.databind.json.JsonMapper;

/**
 * Runs the outbox SQL against a real PostgreSQL, because it depends on Postgres features ({@code
 * FOR UPDATE SKIP LOCKED}, JSONB, partial unique indexes). Needs Docker, so it runs in CI; it is
 * not part of the Docker-free local test set.
 */
@JdbcTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Testcontainers
@Transactional(propagation = Propagation.NOT_SUPPORTED)
class NotificationQueriesTest {

  // BEGIN-CONTAINER (replaced by an embedded Postgres only in Forge's local verification)
  @Container
  static final PostgreSQLContainer<?> postgres =
      new PostgreSQLContainer<>("postgres:16-alpine")
          .withDatabaseName("testdb")
          .withUsername("test")
          .withPassword("test");

  @DynamicPropertySource
  static void configureProperties(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", postgres::getJdbcUrl);
    registry.add("spring.datasource.username", postgres::getUsername);
    registry.add("spring.datasource.password", postgres::getPassword);
  }

  // END-CONTAINER

  @Autowired NamedParameterJdbcTemplate namedJdbc;
  @Autowired JdbcTemplate jdbc;

  NotificationQueries queries;

  @BeforeEach
  void setUp() {
    queries = new NotificationQueries(namedJdbc, JsonMapper.builder().build());
    jdbc.update("DELETE FROM deliveries");
    jdbc.update("DELETE FROM notifications");
  }

  private UUID notification(String status, Instant scheduledAt, String idempotencyKey) {
    return queries
        .insertNotification(
            "TEST",
            "welcome",
            "in_app,email",
            Audience.USERS,
            Map.of("name", "Mia"),
            status,
            scheduledAt,
            idempotencyKey,
            null)
        .orElseThrow()
        .id();
  }

  private UUID queuedNotification() {
    return notification(NotificationStatus.QUEUED, null, null);
  }

  private String deliveryColumn(UUID deliveryId, String column) {
    return jdbc.queryForObject(
        "SELECT CAST(" + column + " AS text) FROM deliveries WHERE id = ?",
        String.class,
        deliveryId);
  }

  private List<UUID> deliveryIds(UUID notificationId) {
    return jdbc.queryForList(
        "SELECT id FROM deliveries WHERE notification_id = ? ORDER BY created_at, id",
        UUID.class,
        notificationId);
  }

  private String notificationStatus(UUID notificationId) {
    return jdbc.queryForObject(
        "SELECT status FROM notifications WHERE id = ?", String.class, notificationId);
  }

  // ------------------------------------------------------------------ enqueue

  @Test
  void insertNotification_withTheSameIdempotencyKeyTwice_insertsOnlyOnce() {
    Optional<NotificationQueries.Inserted> first =
        queries.insertNotification(
            "TEST", "welcome", "in_app", Audience.USERS, Map.of(), "queued", null, "key-1", null);
    Optional<NotificationQueries.Inserted> second =
        queries.insertNotification(
            "TEST", "welcome", "in_app", Audience.USERS, Map.of(), "queued", null, "key-1", null);

    assertThat(first).isPresent();
    assertThat(second).isEmpty();
    assertThat(jdbc.queryForObject("SELECT count(*) FROM notifications", Long.class)).isEqualTo(1);
    Optional<NotificationQueries.Existing> existing = queries.findByIdempotencyKey("key-1");
    assertThat(existing).isPresent();
    assertThat(existing.get().id()).isEqualTo(first.get().id());
    assertThat(existing.get().status()).isEqualTo("queued");
  }

  @Test
  void insertNotification_withoutAKey_allowsRepeats() {
    notification(NotificationStatus.QUEUED, null, null);
    notification(NotificationStatus.QUEUED, null, null);

    assertThat(jdbc.queryForObject("SELECT count(*) FROM notifications", Long.class)).isEqualTo(2);
  }

  @Test
  void findByIdempotencyKey_ofAnUnknownKey_isEmpty() {
    assertThat(queries.findByIdempotencyKey("nope")).isEmpty();
  }

  @Test
  void insertDeliveries_isIdempotentPerRecipientAndChannel() {
    UUID notificationId = queuedNotification();
    UUID recipient = UUID.randomUUID();

    queries.insertDeliveries(notificationId, Set.of(recipient), List.of("in_app", "email"), null);
    queries.insertDeliveries(notificationId, Set.of(recipient), List.of("in_app", "email"), null);

    assertThat(deliveryIds(notificationId)).hasSize(2);
  }

  @Test
  void insertDeliveries_withNoRecipients_doesNothing() {
    UUID notificationId = queuedNotification();

    queries.insertDeliveries(notificationId, Set.of(), List.of("in_app"), null);

    assertThat(deliveryIds(notificationId)).isEmpty();
  }

  @Test
  void findNotification_returnsTheStoredDataAndStatus() {
    UUID id = notification(NotificationStatus.QUEUED, null, null);

    NotificationQueries.NotificationInfo info = queries.findNotification(id).orElseThrow();

    assertThat(info.id()).isEqualTo(id);
    assertThat(info.type()).isEqualTo("TEST");
    assertThat(info.templateKey()).isEqualTo("welcome");
    assertThat(info.status()).isEqualTo("queued");
    assertThat(info.data()).containsExactlyEntriesOf(Map.of("name", "Mia"));
    assertThat(queries.findNotification(UUID.randomUUID())).isEmpty();
  }

  // ------------------------------------------------------------------- worker

  @Test
  void promoteScheduled_movesOnlyDueAcceptedNotificationsToQueued() {
    UUID due =
        notification(NotificationStatus.ACCEPTED, Instant.now().minus(1, ChronoUnit.MINUTES), null);
    UUID future =
        notification(NotificationStatus.ACCEPTED, Instant.now().plus(1, ChronoUnit.HOURS), null);
    UUID unscheduled = notification(NotificationStatus.ACCEPTED, null, null);

    int promoted = queries.promoteScheduled();

    assertThat(promoted).isEqualTo(1);
    assertThat(notificationStatus(due)).isEqualTo("queued");
    assertThat(notificationStatus(future)).isEqualTo("accepted");
    assertThat(notificationStatus(unscheduled)).isEqualTo("accepted");
  }

  @Test
  void claimDue_ignoresDeliveriesScheduledInTheFuture() {
    UUID notificationId = queuedNotification();
    queries.insertDeliveries(
        notificationId,
        Set.of(UUID.randomUUID()),
        List.of("in_app"),
        Instant.now().plus(1, ChronoUnit.HOURS));

    assertThat(queries.claimDue(10, 300)).isEmpty();
  }

  @Test
  void claimDue_returnsDueDeliveriesOnceAndHoldsThemForTheLease() {
    UUID notificationId = queuedNotification();
    UUID recipient = UUID.randomUUID();
    queries.insertDeliveries(notificationId, Set.of(recipient), List.of("in_app", "email"), null);

    List<NotificationQueries.DeliveryJob> first = queries.claimDue(10, 3600);
    List<NotificationQueries.DeliveryJob> second = queries.claimDue(10, 3600);

    assertThat(first).hasSize(2);
    assertThat(first)
        .allSatisfy(
            job -> {
              assertThat(job.notificationId()).isEqualTo(notificationId);
              assertThat(job.recipientId()).isEqualTo(recipient);
              assertThat(job.attemptCount()).isZero();
            });
    assertThat(second).isEmpty();
  }

  @Test
  void claimDue_respectsTheBatchSize() {
    UUID notificationId = queuedNotification();
    Set<UUID> recipients = new HashSet<>();
    for (int i = 0; i < 5; i++) {
      recipients.add(UUID.randomUUID());
    }
    queries.insertDeliveries(notificationId, recipients, List.of("in_app"), null);

    assertThat(queries.claimDue(3, 300)).hasSize(3);
    assertThat(queries.claimDue(3, 300)).hasSize(2);
  }

  @Test
  void claimDue_reclaimsADeliveryOnceItsLeaseHasExpired() {
    UUID notificationId = queuedNotification();
    queries.insertDeliveries(notificationId, Set.of(UUID.randomUUID()), List.of("in_app"), null);
    List<NotificationQueries.DeliveryJob> claimed = queries.claimDue(10, 3600);
    assertThat(queries.claimDue(10, 3600)).isEmpty();

    jdbc.update(
        "UPDATE deliveries SET next_retry_at = now() - interval '1 second' WHERE id = ?",
        claimed.get(0).id());

    assertThat(queries.claimDue(10, 3600)).extracting("id").containsExactly(claimed.get(0).id());
  }

  @Test
  void claimDue_neverReturnsTheSameDeliveryToTwoConcurrentWorkers() throws Exception {
    UUID notificationId = queuedNotification();
    Set<UUID> recipients = new HashSet<>();
    for (int i = 0; i < 40; i++) {
      recipients.add(UUID.randomUUID());
    }
    queries.insertDeliveries(notificationId, recipients, List.of("in_app"), null);

    int workers = 4;
    ExecutorService pool = Executors.newFixedThreadPool(workers);
    CountDownLatch start = new CountDownLatch(1);
    List<Future<List<NotificationQueries.DeliveryJob>>> results = new ArrayList<>();
    for (int i = 0; i < workers; i++) {
      results.add(
          pool.submit(
              () -> {
                start.await();
                return queries.claimDue(40, 300);
              }));
    }
    start.countDown();
    List<UUID> claimedIds = new ArrayList<>();
    for (Future<List<NotificationQueries.DeliveryJob>> result : results) {
      result.get().forEach(job -> claimedIds.add(job.id()));
    }
    pool.shutdownNow();

    assertThat(claimedIds).hasSize(40).doesNotHaveDuplicates();
  }

  @Test
  void scheduleRetry_countsTheAttemptAndHidesTheDeliveryUntilTheDelayPasses() {
    UUID notificationId = queuedNotification();
    queries.insertDeliveries(notificationId, Set.of(UUID.randomUUID()), List.of("email"), null);
    UUID deliveryId = queries.claimDue(10, 0).get(0).id();

    queries.scheduleRetry(deliveryId, 1, 3600, "smtp down");

    assertThat(queries.claimDue(10, 300)).isEmpty();
    assertThat(deliveryColumn(deliveryId, "attempt_count")).isEqualTo("1");
    assertThat(deliveryColumn(deliveryId, "last_error")).isEqualTo("smtp down");
    assertThat(deliveryColumn(deliveryId, "status")).isEqualTo("pending");
  }

  @Test
  void markSent_markSkipped_markFailedAndMarkInAppSent_updateTheDelivery() {
    UUID notificationId = queuedNotification();
    queries.insertDeliveries(
        notificationId,
        Set.of(UUID.randomUUID(), UUID.randomUUID(), UUID.randomUUID(), UUID.randomUUID()),
        List.of("email"),
        null);
    List<UUID> ids = deliveryIds(notificationId);

    queries.markSent(ids.get(0), "msg-1");
    queries.markSkipped(ids.get(1), DeliveryStatus.SKIP_OPTED_OUT);
    queries.markFailed(ids.get(2), 5, "gave up");
    queries.markInAppSent(ids.get(3), "Title", "Body");

    assertThat(deliveryColumn(ids.get(0), "status")).isEqualTo("sent");
    assertThat(deliveryColumn(ids.get(0), "provider_message_id")).isEqualTo("msg-1");
    assertThat(deliveryColumn(ids.get(1), "status")).isEqualTo("skipped");
    assertThat(deliveryColumn(ids.get(1), "skip_reason")).isEqualTo("opted_out");
    assertThat(deliveryColumn(ids.get(2), "status")).isEqualTo("failed");
    assertThat(deliveryColumn(ids.get(2), "attempt_count")).isEqualTo("5");
    assertThat(deliveryColumn(ids.get(2), "last_error")).isEqualTo("gave up");
    assertThat(deliveryColumn(ids.get(3), "status")).isEqualTo("sent");
    assertThat(deliveryColumn(ids.get(3), "title")).isEqualTo("Title");
    assertThat(deliveryColumn(ids.get(3), "body")).isEqualTo("Body");
  }

  // ------------------------------------------------------------------- roll-up

  @Test
  void rollUp_completesANotificationWhoseDeliveriesAreAllSentOrSkipped() {
    UUID id = queuedNotification();
    queries.insertDeliveries(
        id, Set.of(UUID.randomUUID(), UUID.randomUUID()), List.of("email"), null);
    List<UUID> ids = deliveryIds(id);
    queries.markSent(ids.get(0), null);
    queries.markSkipped(ids.get(1), DeliveryStatus.SKIP_OPTED_OUT);

    queries.rollUp();

    assertThat(notificationStatus(id)).isEqualTo("completed");
  }

  @Test
  void rollUp_marksPartiallyFailedWhenSomeSentAndSomeFailed() {
    UUID id = queuedNotification();
    queries.insertDeliveries(
        id, Set.of(UUID.randomUUID(), UUID.randomUUID()), List.of("email"), null);
    List<UUID> ids = deliveryIds(id);
    queries.markSent(ids.get(0), null);
    queries.markFailed(ids.get(1), 5, "boom");

    queries.rollUp();

    assertThat(notificationStatus(id)).isEqualTo("partially_failed");
  }

  @Test
  void rollUp_marksFailedWhenEveryDeliveryFailed() {
    UUID id = queuedNotification();
    queries.insertDeliveries(id, Set.of(UUID.randomUUID()), List.of("email"), null);
    queries.markFailed(deliveryIds(id).get(0), 5, "boom");

    queries.rollUp();

    assertThat(notificationStatus(id)).isEqualTo("failed");
  }

  @Test
  void rollUp_leavesANotificationWithAPendingDeliveryQueued() {
    UUID id = queuedNotification();
    queries.insertDeliveries(
        id, Set.of(UUID.randomUUID(), UUID.randomUUID()), List.of("email"), null);
    queries.markSent(deliveryIds(id).get(0), null);

    int updated = queries.rollUp();

    assertThat(updated).isZero();
    assertThat(notificationStatus(id)).isEqualTo("queued");
  }

  @Test
  void rollUp_doesNotTouchNotificationsThatAreNotQueued() {
    UUID id =
        notification(NotificationStatus.ACCEPTED, Instant.now().plus(1, ChronoUnit.HOURS), null);
    queries.insertDeliveries(id, Set.of(UUID.randomUUID()), List.of("email"), null);
    queries.markSent(deliveryIds(id).get(0), null);

    queries.rollUp();

    assertThat(notificationStatus(id)).isEqualTo("accepted");
  }

  // --------------------------------------------------------------------- inbox

  private UUID sentInApp(UUID notificationId, UUID recipient, String title) {
    queries.insertDeliveries(notificationId, Set.of(recipient), List.of("in_app"), null);
    UUID deliveryId =
        jdbc.queryForObject(
            "SELECT id FROM deliveries WHERE notification_id = ? AND recipient_id = ? AND channel = 'in_app'",
            UUID.class,
            notificationId,
            recipient);
    queries.markInAppSent(deliveryId, title, "body of " + title);
    return deliveryId;
  }

  @Test
  void inbox_listsSentInAppDeliveriesNewestFirstAndPages() throws InterruptedException {
    UUID recipient = UUID.randomUUID();
    UUID a = sentInApp(queuedNotification(), recipient, "first");
    Thread.sleep(5);
    UUID b = sentInApp(queuedNotification(), recipient, "second");
    Thread.sleep(5);
    UUID c = sentInApp(queuedNotification(), recipient, "third");

    List<NotificationQueries.InboxRow> page1 = queries.inbox(recipient, 2, 0);
    List<NotificationQueries.InboxRow> page2 = queries.inbox(recipient, 2, 2);

    assertThat(page1).extracting("id").containsExactly(c, b);
    assertThat(page2).extracting("id").containsExactly(a);
    assertThat(page1.get(0).title()).isEqualTo("third");
    assertThat(page1.get(0).body()).isEqualTo("body of third");
    assertThat(page1.get(0).type()).isEqualTo("TEST");
    assertThat(page1.get(0).read()).isFalse();
    assertThat(queries.inboxCount(recipient)).isEqualTo(3);
  }

  @Test
  void inbox_excludesEmailPendingDismissedAndOtherRecipients() {
    UUID recipient = UUID.randomUUID();
    UUID other = UUID.randomUUID();
    UUID notificationId = queuedNotification();
    UUID visible = sentInApp(notificationId, recipient, "visible");
    UUID dismissed = sentInApp(queuedNotification(), recipient, "dismissed");
    queries.dismiss(dismissed, recipient);
    sentInApp(queuedNotification(), other, "someone else's");
    queries.insertDeliveries(notificationId, Set.of(recipient), List.of("email"), null);
    queries.insertDeliveries(queuedNotification(), Set.of(recipient), List.of("in_app"), null);

    assertThat(queries.inbox(recipient, 10, 0)).extracting("id").containsExactly(visible);
    assertThat(queries.inboxCount(recipient)).isEqualTo(1);
  }

  @Test
  void markRead_isIdempotentAndKeepsTheFirstReadTime() throws InterruptedException {
    UUID recipient = UUID.randomUUID();
    UUID delivery = sentInApp(queuedNotification(), recipient, "hello");

    assertThat(queries.unreadCount(recipient)).isEqualTo(1);
    assertThat(queries.markRead(delivery, recipient)).isTrue();
    String firstReadAt = deliveryColumn(delivery, "read_at");
    Thread.sleep(5);
    assertThat(queries.markRead(delivery, recipient)).isTrue();

    assertThat(deliveryColumn(delivery, "read_at")).isEqualTo(firstReadAt);
    assertThat(queries.unreadCount(recipient)).isZero();
    assertThat(queries.inbox(recipient, 10, 0).get(0).read()).isTrue();
  }

  @Test
  void markReadAndDismiss_forSomeoneElsesDelivery_returnFalseAndChangeNothing() {
    UUID owner = UUID.randomUUID();
    UUID intruder = UUID.randomUUID();
    UUID delivery = sentInApp(queuedNotification(), owner, "private");

    assertThat(queries.markRead(delivery, intruder)).isFalse();
    assertThat(queries.dismiss(delivery, intruder)).isFalse();

    assertThat(deliveryColumn(delivery, "read_at")).isNull();
    assertThat(deliveryColumn(delivery, "dismissed_at")).isNull();
    assertThat(queries.markRead(UUID.randomUUID(), owner)).isFalse();
  }

  @Test
  void dismiss_hidesTheDeliveryFromTheInboxButKeepsTheRowAndIsOnlyPossibleOnce() {
    UUID recipient = UUID.randomUUID();
    UUID delivery = sentInApp(queuedNotification(), recipient, "bye");

    assertThat(queries.dismiss(delivery, recipient)).isTrue();
    assertThat(queries.dismiss(delivery, recipient)).isFalse();

    assertThat(queries.inbox(recipient, 10, 0)).isEmpty();
    assertThat(queries.markRead(delivery, recipient)).isFalse();
    assertThat(
            jdbc.queryForObject(
                "SELECT count(*) FROM deliveries WHERE id = ?", Long.class, delivery))
        .isEqualTo(1);
  }

  @Test
  void markAllRead_marksOnlyTheRecipientsUnreadDeliveries() {
    UUID recipient = UUID.randomUUID();
    UUID other = UUID.randomUUID();
    sentInApp(queuedNotification(), recipient, "one");
    sentInApp(queuedNotification(), recipient, "two");
    sentInApp(queuedNotification(), other, "not mine");

    int marked = queries.markAllRead(recipient);

    assertThat(marked).isEqualTo(2);
    assertThat(queries.unreadCount(recipient)).isZero();
    assertThat(queries.unreadCount(other)).isEqualTo(1);
    assertThat(queries.markAllRead(recipient)).isZero();
  }

  @Test
  void deleteDeliveriesOf_removesOnlyThatRecipientsDeliveries() {
    UUID recipient = UUID.randomUUID();
    UUID other = UUID.randomUUID();
    sentInApp(queuedNotification(), recipient, "one");
    sentInApp(queuedNotification(), other, "two");

    int deleted = queries.deleteDeliveriesOf(recipient);

    assertThat(deleted).isEqualTo(1);
    assertThat(queries.inboxCount(recipient)).isZero();
    assertThat(queries.inboxCount(other)).isEqualTo(1);
  }
}
