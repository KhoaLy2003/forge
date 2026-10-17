package {{ base_package }}.notification;

import java.util.UUID;

/**
 * Delivers one rendered message over an external channel (email, push, SMS, ...). The delivery
 * worker picks the sender whose {@link #channel()} matches the delivery. To add a channel: add a
 * value to {@link NotificationChannel}, allow it in the migration's channel checks, add templates
 * for it, and register a bean implementing this interface.
 *
 * <p>Implementations must not throw for expected problems: report them through {@link SendOutcome}.
 * They must never log recipient addresses, message bodies or provider tokens. The in-app channel
 * needs no sender because it only stores the rendered text.
 */
public interface ChannelSender {

  /**
   * Returns the channel this sender serves.
   *
   * @return the channel
   */
  NotificationChannel channel();

  /**
   * Sends one message.
   *
   * @param request what to send and to whom
   * @return the outcome; never throws for provider or configuration problems
   */
  SendOutcome send(SendRequest request);

  /**
   * One message to send.
   *
   * @param deliveryId the delivery being processed
   * @param recipientId the recipient id
   * @param recipient the recipient's contact details from the {@link RecipientDirectory}
   * @param title the rendered title or subject
   * @param body the rendered body
   */
  record SendRequest(
      UUID deliveryId, UUID recipientId, Recipient recipient, String title, String body) {}

  /** How a send attempt ended. */
  enum Result {
    /** The provider accepted the message (this is not a delivery receipt). */
    SENT,
    /** The channel is not configured in this environment; the delivery is skipped, not failed. */
    NOT_CONFIGURED,
    /** A transient or unknown failure; the delivery may be retried. */
    FAILED
  }

  /**
   * The outcome of a send attempt.
   *
   * @param result how the attempt ended
   * @param providerMessageId the provider's message id when {@link Result#SENT}, else {@code null}
   */
  record SendOutcome(Result result, String providerMessageId) {

    /**
     * Creates a successful outcome.
     *
     * @param providerMessageId the provider's message id, or {@code null} if it has none
     * @return a {@link Result#SENT} outcome
     */
    public static SendOutcome sent(String providerMessageId) {
      return new SendOutcome(Result.SENT, providerMessageId);
    }

    /**
     * Creates a "channel not configured" outcome.
     *
     * @return a {@link Result#NOT_CONFIGURED} outcome
     */
    public static SendOutcome notConfigured() {
      return new SendOutcome(Result.NOT_CONFIGURED, null);
    }

    /**
     * Creates a retryable failure outcome.
     *
     * @return a {@link Result#FAILED} outcome
     */
    public static SendOutcome failed() {
      return new SendOutcome(Result.FAILED, null);
    }
  }
}
