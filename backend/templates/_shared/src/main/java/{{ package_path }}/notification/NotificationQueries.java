package {{ base_package }}.notification;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.jdbc.core.namedparam.SqlParameterSource;
import org.springframework.stereotype.Repository;
import tools.jackson.databind.ObjectMapper;

/**
 * All SQL for the {@code notifications} and {@code deliveries} outbox tables. These tables have no
 * JPA entity: the pipeline needs {@code INSERT ... ON CONFLICT DO NOTHING}, {@code FOR UPDATE SKIP
 * LOCKED} and set-based updates, so everything goes through {@link NamedParameterJdbcTemplate}.
 * Only fixed SQL fragments reach a statement; every value is a bind parameter.
 *
 * <p>Deliberately absent compared with a full notification service: audience fan-out ("everyone"),
 * cancellation and administrative listing. Add them here if your project needs them.
 */
@Repository
@RequiredArgsConstructor
public class NotificationQueries {

  private final NamedParameterJdbcTemplate jdbc;
  private final ObjectMapper objectMapper;

  /**
   * A freshly inserted notification.
   *
   * @param id the notification id
   * @param createdAt when it was recorded
   */
  public record Inserted(UUID id, Instant createdAt) {}

  /**
   * An existing notification found by idempotency key.
   *
   * @param id the notification id
   * @param status its current status
   * @param createdAt when it was recorded
   */
  public record Existing(UUID id, String status, Instant createdAt) {}

  /**
   * A delivery claimed by the worker.
   *
   * @param id the delivery id
   * @param notificationId the owning notification
   * @param recipientId the recipient id
   * @param channel the channel string
   * @param attemptCount failed attempts so far
   */
  public record DeliveryJob(
      UUID id, UUID notificationId, UUID recipientId, String channel, int attemptCount) {}

  /**
   * The notification data the processor needs.
   *
   * @param id the notification id
   * @param type the trigger name
   * @param templateKey the template key
   * @param status the current status
   * @param data template values and context
   */
  public record NotificationInfo(
      UUID id, String type, String templateKey, String status, Map<String, String> data) {}

  /**
   * One inbox row.
   *
   * @param id the delivery id
   * @param notificationId the notification this delivery belongs to
   * @param type the trigger name
   * @param title the rendered title
   * @param body the rendered body
   * @param createdAt when the delivery was created
   * @param read whether the recipient has read it
   */
  public record InboxRow(
      UUID id,
      UUID notificationId,
      String type,
      String title,
      String body,
      Instant createdAt,
      boolean read) {}

  // ---------------------------------------------------------------- enqueue

  /**
   * Inserts a notification, doing nothing when the idempotency key already exists.
   *
   * @param type the trigger name
   * @param templateKey the template key
   * @param channelsCsv the comma-separated channel strings
   * @param audienceType the audience type
   * @param data template values and context
   * @param status the initial status
   * @param scheduledAt the schedule, or {@code null}
   * @param idempotencyKey the idempotency key, or {@code null}
   * @param createdBy the acting user id, or {@code null}
   * @return the inserted row, or empty when the key already existed
   */
  public Optional<Inserted> insertNotification(
      String type,
      String templateKey,
      String channelsCsv,
      String audienceType,
      Map<String, String> data,
      String status,
      Instant scheduledAt,
      String idempotencyKey,
      UUID createdBy) {
    MapSqlParameterSource params =
        new MapSqlParameterSource()
            .addValue("type", type)
            .addValue("templateKey", templateKey)
            .addValue("channels", channelsCsv)
            .addValue("audienceType", audienceType)
            .addValue("data", objectMapper.writeValueAsString(data))
            .addValue("status", status)
            .addValue("scheduledAt", scheduledAt == null ? null : Timestamp.from(scheduledAt))
            .addValue("idempotencyKey", idempotencyKey)
            .addValue("createdBy", createdBy);
    return jdbc
        .query(
            "INSERT INTO notifications (type, template_key, channels, audience_type, data, status,"
                + " scheduled_at, idempotency_key, created_by) VALUES (:type, :templateKey,"
                + " :channels, :audienceType, CAST(:data AS jsonb), :status, CAST(:scheduledAt AS"
                + " timestamptz), :idempotencyKey, CAST(:createdBy AS uuid)) ON CONFLICT"
                + " (idempotency_key) WHERE idempotency_key IS NOT NULL DO NOTHING RETURNING id,"
                + " created_at",
            params,
            (rs, rowNum) ->
                new Inserted(
                    rs.getObject("id", UUID.class), rs.getTimestamp("created_at").toInstant()))
        .stream()
        .findFirst();
  }

  /**
   * Looks a notification up by idempotency key.
   *
   * @param idempotencyKey the idempotency key
   * @return the notification created with this key, if any
   */
  public Optional<Existing> findByIdempotencyKey(String idempotencyKey) {
    return jdbc
        .query(
            "SELECT id, status, created_at FROM notifications WHERE idempotency_key = :key",
            new MapSqlParameterSource("key", idempotencyKey),
            (rs, rowNum) ->
                new Existing(
                    rs.getObject("id", UUID.class),
                    rs.getString("status"),
                    rs.getTimestamp("created_at").toInstant()))
        .stream()
        .findFirst();
  }

  /**
   * Inserts one pending delivery per recipient and channel; existing combinations are ignored.
   *
   * @param notificationId the owning notification
   * @param recipients the recipient ids
   * @param channels the channel strings
   * @param dueAt when the deliveries become due, or {@code null} for now
   */
  public void insertDeliveries(
      UUID notificationId,
      Collection<UUID> recipients,
      Collection<String> channels,
      Instant dueAt) {
    List<SqlParameterSource> batch = new ArrayList<>(recipients.size() * channels.size());
    Timestamp due = dueAt == null ? null : Timestamp.from(dueAt);
    for (UUID recipient : recipients) {
      for (String channel : channels) {
        batch.add(
            new MapSqlParameterSource()
                .addValue("notificationId", notificationId)
                .addValue("recipientId", recipient)
                .addValue("channel", channel)
                .addValue("due", due));
      }
    }
    if (batch.isEmpty()) {
      return;
    }
    jdbc.batchUpdate(
        "INSERT INTO deliveries (notification_id, recipient_id, channel, next_retry_at) VALUES"
            + " (:notificationId, :recipientId, :channel, coalesce(CAST(:due AS timestamptz),"
            + " now())) ON CONFLICT (notification_id, recipient_id, channel) DO NOTHING",
        batch.toArray(SqlParameterSource[]::new));
  }

  // ----------------------------------------------------------------- worker

  /**
   * Moves scheduled notifications whose time has come from accepted to queued.
   *
   * @return the number promoted
   */
  public int promoteScheduled() {
    return jdbc.update(
        "UPDATE notifications SET status = 'queued', updated_at = now() WHERE status = 'accepted'"
            + " AND scheduled_at IS NOT NULL AND scheduled_at <= now()",
        new MapSqlParameterSource());
  }

  /**
   * Claims due pending deliveries by pushing their {@code next_retry_at} forward by the lease, so
   * another worker (or a later tick) skips them while they are being processed. A crash lets the
   * lease expire and the delivery is retried.
   *
   * @param batch the maximum number to claim
   * @param leaseSeconds the lease length in seconds
   * @return the claimed deliveries
   */
  public List<DeliveryJob> claimDue(int batch, int leaseSeconds) {
    return jdbc.query(
        "UPDATE deliveries SET next_retry_at = now() + make_interval(secs => CAST(:lease AS double"
            + " precision)), updated_at = now() WHERE id IN (SELECT id FROM deliveries WHERE status"
            + " = 'pending' AND next_retry_at <= now() ORDER BY next_retry_at LIMIT :batch FOR"
            + " UPDATE SKIP LOCKED) RETURNING id, notification_id, recipient_id, channel,"
            + " attempt_count",
        new MapSqlParameterSource().addValue("lease", leaseSeconds).addValue("batch", batch),
        (rs, rowNum) ->
            new DeliveryJob(
                rs.getObject("id", UUID.class),
                rs.getObject("notification_id", UUID.class),
                rs.getObject("recipient_id", UUID.class),
                rs.getString("channel"),
                rs.getInt("attempt_count")));
  }

  /**
   * Loads the notification data the processor needs.
   *
   * @param id the notification id
   * @return the notification data for processing, if it exists
   */
  public Optional<NotificationInfo> findNotification(UUID id) {
    return jdbc
        .query(
            "SELECT id, type, template_key, status, data::text AS data FROM notifications WHERE id"
                + " = :id",
            new MapSqlParameterSource("id", id),
            (rs, rowNum) ->
                new NotificationInfo(
                    rs.getObject("id", UUID.class),
                    rs.getString("type"),
                    rs.getString("template_key"),
                    rs.getString("status"),
                    parseData(rs.getString("data"))))
        .stream()
        .findFirst();
  }

  private Map<String, String> parseData(String json) {
    Map<String, String> out = new LinkedHashMap<>();
    Map<?, ?> raw = objectMapper.readValue(json, Map.class);
    raw.forEach((k, v) -> out.put(String.valueOf(k), v == null ? "" : String.valueOf(v)));
    return out;
  }

  /**
   * Marks an in-app delivery sent, storing its rendered text.
   *
   * @param id the delivery id
   * @param title the rendered title
   * @param body the rendered body
   */
  public void markInAppSent(UUID id, String title, String body) {
    jdbc.update(
        "UPDATE deliveries SET status = 'sent', title = :title, body = :body, updated_at = now()"
            + " WHERE id = :id",
        new MapSqlParameterSource()
            .addValue("id", id)
            .addValue("title", title)
            .addValue("body", body));
  }

  /**
   * Marks a provider-backed (for example email) delivery sent.
   *
   * @param id the delivery id
   * @param providerMessageId the provider's message id, or {@code null}
   */
  public void markSent(UUID id, String providerMessageId) {
    jdbc.update(
        "UPDATE deliveries SET status = 'sent', provider_message_id = :pid, last_error = NULL,"
            + " updated_at = now() WHERE id = :id",
        new MapSqlParameterSource().addValue("id", id).addValue("pid", providerMessageId));
  }

  /**
   * Marks a delivery intentionally not sent.
   *
   * @param id the delivery id
   * @param reason one of the {@code DeliveryStatus.SKIP_*} reasons
   */
  public void markSkipped(UUID id, String reason) {
    jdbc.update(
        "UPDATE deliveries SET status = 'skipped', skip_reason = :reason, updated_at = now() WHERE"
            + " id = :id",
        new MapSqlParameterSource().addValue("id", id).addValue("reason", reason));
  }

  /**
   * Records a failed attempt and schedules the next one.
   *
   * @param id the delivery id
   * @param attemptCount the new failed-attempt count
   * @param delaySeconds seconds until the next attempt
   * @param error the error text, at most 500 characters
   */
  public void scheduleRetry(UUID id, int attemptCount, int delaySeconds, String error) {
    jdbc.update(
        "UPDATE deliveries SET attempt_count = :attempts, next_retry_at = now() +"
            + " make_interval(secs => CAST(:delay AS double precision)), last_error = :error,"
            + " updated_at = now() WHERE id = :id",
        new MapSqlParameterSource()
            .addValue("id", id)
            .addValue("attempts", attemptCount)
            .addValue("delay", delaySeconds)
            .addValue("error", error));
  }

  /**
   * Records the final failed attempt.
   *
   * @param id the delivery id
   * @param attemptCount the final failed-attempt count
   * @param error the error text, at most 500 characters
   */
  public void markFailed(UUID id, int attemptCount, String error) {
    jdbc.update(
        "UPDATE deliveries SET status = 'failed', attempt_count = :attempts, last_error = :error,"
            + " updated_at = now() WHERE id = :id",
        new MapSqlParameterSource()
            .addValue("id", id)
            .addValue("attempts", attemptCount)
            .addValue("error", error));
  }

  /**
   * Computes the final status of queued notifications that have deliveries and none pending.
   *
   * @return the number of notifications updated
   */
  public int rollUp() {
    return jdbc.update(
        "UPDATE notifications n SET updated_at = now(), status = CASE WHEN f.failed = 0 THEN"
            + " 'completed' WHEN f.sent = 0 THEN 'failed' ELSE 'partially_failed' END FROM (SELECT"
            + " notification_id, count(*) FILTER (WHERE status = 'failed') AS failed, count(*)"
            + " FILTER (WHERE status = 'sent') AS sent FROM deliveries GROUP BY notification_id) f"
            + " WHERE f.notification_id = n.id AND n.status = 'queued' AND NOT EXISTS (SELECT 1"
            + " FROM deliveries p WHERE p.notification_id = n.id AND p.status = 'pending')",
        new MapSqlParameterSource());
  }

  // ------------------------------------------------------------------ inbox

  /**
   * Lists a recipient's visible inbox.
   *
   * @param recipientId the recipient
   * @param limit the page size
   * @param offset rows to skip
   * @return the recipient's sent, not dismissed in-app deliveries, newest first
   */
  public List<InboxRow> inbox(UUID recipientId, int limit, long offset) {
    return jdbc.query(
        "SELECT d.id, d.notification_id, n.type, d.title, d.body, d.created_at, d.read_at FROM"
            + " deliveries d JOIN notifications n ON n.id = d.notification_id WHERE d.recipient_id"
            + " = :recipientId AND d.channel = 'in_app' AND d.status = 'sent' AND d.dismissed_at"
            + " IS NULL ORDER BY d.created_at DESC, d.id DESC LIMIT :limit OFFSET :offset",
        new MapSqlParameterSource()
            .addValue("recipientId", recipientId)
            .addValue("limit", limit)
            .addValue("offset", offset),
        (rs, rowNum) ->
            new InboxRow(
                rs.getObject("id", UUID.class),
                rs.getObject("notification_id", UUID.class),
                rs.getString("type"),
                rs.getString("title"),
                rs.getString("body"),
                rs.getTimestamp("created_at").toInstant(),
                rs.getTimestamp("read_at") != null));
  }

  /**
   * Counts a recipient's visible inbox.
   *
   * @param recipientId the recipient
   * @return the number of sent, not dismissed in-app deliveries
   */
  public long inboxCount(UUID recipientId) {
    Long count =
        jdbc.queryForObject(
            "SELECT count(*) FROM deliveries WHERE recipient_id = :recipientId AND channel ="
                + " 'in_app' AND status = 'sent' AND dismissed_at IS NULL",
            new MapSqlParameterSource("recipientId", recipientId),
            Long.class);
    return count == null ? 0 : count;
  }

  /**
   * Counts a recipient's unread inbox.
   *
   * @param recipientId the recipient
   * @return the number of unread, visible in-app deliveries
   */
  public long unreadCount(UUID recipientId) {
    Long count =
        jdbc.queryForObject(
            "SELECT count(*) FROM deliveries WHERE recipient_id = :recipientId AND channel ="
                + " 'in_app' AND status = 'sent' AND dismissed_at IS NULL AND read_at IS NULL",
            new MapSqlParameterSource("recipientId", recipientId),
            Long.class);
    return count == null ? 0 : count;
  }

  /**
   * Marks one of the recipient's in-app deliveries read (idempotent; the first read time is kept).
   *
   * @param deliveryId the delivery id
   * @param recipientId the recipient
   * @return whether a visible delivery of this recipient with this id exists
   */
  public boolean markRead(UUID deliveryId, UUID recipientId) {
    return jdbc.update(
            "UPDATE deliveries SET read_at = coalesce(read_at, now()), updated_at = now() WHERE id"
                + " = :id AND recipient_id = :recipientId AND channel = 'in_app' AND status ="
                + " 'sent' AND dismissed_at IS NULL",
            new MapSqlParameterSource()
                .addValue("id", deliveryId)
                .addValue("recipientId", recipientId))
        > 0;
  }

  /**
   * Marks all of a recipient's unread in-app deliveries read.
   *
   * @param recipientId the recipient
   * @return the number of deliveries marked read
   */
  public int markAllRead(UUID recipientId) {
    return jdbc.update(
        "UPDATE deliveries SET read_at = now(), updated_at = now() WHERE recipient_id ="
            + " :recipientId AND channel = 'in_app' AND status = 'sent' AND dismissed_at IS NULL"
            + " AND read_at IS NULL",
        new MapSqlParameterSource("recipientId", recipientId));
  }

  /**
   * Removes one in-app delivery from the recipient's inbox. The row stays so delivery statistics
   * are unchanged; only the inbox hides it.
   *
   * @param deliveryId the delivery id
   * @param recipientId the recipient
   * @return whether a visible delivery of this recipient with this id existed
   */
  public boolean dismiss(UUID deliveryId, UUID recipientId) {
    return jdbc.update(
            "UPDATE deliveries SET dismissed_at = now(), updated_at = now() WHERE id = :id AND"
                + " recipient_id = :recipientId AND channel = 'in_app' AND status = 'sent' AND"
                + " dismissed_at IS NULL",
            new MapSqlParameterSource()
                .addValue("id", deliveryId)
                .addValue("recipientId", recipientId))
        > 0;
  }

  /**
   * Deletes every delivery of a recipient (for example when their account is deleted).
   *
   * @param recipientId the recipient
   * @return the number of deliveries deleted
   */
  public int deleteDeliveriesOf(UUID recipientId) {
    return jdbc.update(
        "DELETE FROM deliveries WHERE recipient_id = :recipientId",
        new MapSqlParameterSource("recipientId", recipientId));
  }
}
