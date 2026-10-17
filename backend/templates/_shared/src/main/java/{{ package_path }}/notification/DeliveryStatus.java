package {{ base_package }}.notification;

/** Statuses and skip reasons of a {@code deliveries} row, stored as these exact strings. */
public final class DeliveryStatus {

  /** Waiting to be sent; {@code next_retry_at} says when. */
  public static final String PENDING = "pending";

  /** The provider accepted it (this is not a delivery receipt). */
  public static final String SENT = "sent";

  /** Gave up after the maximum number of attempts. */
  public static final String FAILED = "failed";

  /** Intentionally not sent; see the {@code SKIP_*} reasons. */
  public static final String SKIPPED = "skipped";

  /** Skip reason: the recipient turned this channel off in their preferences. */
  public static final String SKIP_OPTED_OUT = "opted_out";

  /** Skip reason: no active template for the channel and locale (including the default locale). */
  public static final String SKIP_NO_TEMPLATE = "no_template";

  /** Skip reason: SMTP is not configured. */
  public static final String SKIP_EMAIL_NOT_CONFIGURED = "email_not_configured";

  /** Skip reason: the RecipientDirectory could not resolve the recipient's details. */
  public static final String SKIP_RECIPIENT_UNRESOLVED = "recipient_unresolved";

  /** Skip reason: the notification was cancelled. */
  public static final String SKIP_CANCELLED = "cancelled";

  private DeliveryStatus() {}
}
