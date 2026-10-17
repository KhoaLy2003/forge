package {{ base_package }}.notification;

import java.util.Arrays;

/**
 * A delivery channel. {@link #dbValue()} is the string stored in the database and exposed by the
 * API. New channels are added here, in the migration's channel check, and with a {@link
 * ChannelSender} bean.
 */
public enum NotificationChannel {
  IN_APP("in_app"),
  EMAIL("email");

  private final String dbValue;

  NotificationChannel(String dbValue) {
    this.dbValue = dbValue;
  }

  /**
   * Returns the stored form of this channel.
   *
   * @return the value stored in {@code deliveries.channel} and exposed by the API
   */
  public String dbValue() {
    return dbValue;
  }

  /**
   * Looks a channel up by its stored value.
   *
   * @param value a stored channel value such as {@code "in_app"}
   * @return the matching channel
   * @throws IllegalArgumentException if the value is unknown
   */
  public static NotificationChannel fromDb(String value) {
    return Arrays.stream(values())
        .filter(channel -> channel.dbValue.equals(value))
        .findFirst()
        .orElseThrow(() -> new IllegalArgumentException("Unknown channel: " + value));
  }
}
