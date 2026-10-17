package {{ base_package }}.notification;

import java.util.Set;
import java.util.UUID;

/**
 * Who receives a notification: an explicit set of recipient ids. What a recipient id refers to is
 * up to the project (see {@link RecipientDirectory}).
 *
 * @param type the audience type; only {@link #USERS} is supported
 * @param userIds the explicit recipients; copied and unmodifiable
 */
public record Audience(String type, Set<UUID> userIds) {

  /** Audience type: an explicit set of recipient ids. */
  public static final String USERS = "users";

  /** Defensively copies the recipient ids. */
  public Audience {
    userIds = Set.copyOf(userIds);
  }

  /**
   * Creates an explicit audience.
   *
   * @param ids the recipients
   * @return an audience of exactly these recipients
   */
  public static Audience users(Set<UUID> ids) {
    return new Audience(USERS, ids);
  }
}
