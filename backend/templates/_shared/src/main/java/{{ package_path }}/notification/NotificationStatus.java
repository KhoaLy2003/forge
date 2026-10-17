package {{ base_package }}.notification;

/** Lifecycle statuses of a {@code notifications} row, stored as these exact strings. */
public final class NotificationStatus {

  /** Waiting for its schedule to come due. */
  public static final String ACCEPTED = "accepted";

  /** Deliveries exist and are being processed. */
  public static final String QUEUED = "queued";

  /** No pending deliveries and none failed. */
  public static final String COMPLETED = "completed";

  /** No pending deliveries; some failed and some were sent. */
  public static final String PARTIALLY_FAILED = "partially_failed";

  /** No pending deliveries; some failed and none were sent. */
  public static final String FAILED = "failed";

  /** Cancelled before completion; pending deliveries are skipped. */
  public static final String CANCELLED = "cancelled";

  private NotificationStatus() {}
}
