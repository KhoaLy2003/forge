package {{ base_package }}.notification;

import java.util.Optional;
import java.util.UUID;

/**
 * Identifies who is calling the inbox API. The generated project has no authentication, so it
 * cannot know; implement this interface as a Spring bean that reads the caller from your security
 * context (for example the JWT subject). Without a bean, {@link #NONE} is used: there is no caller
 * and every {@code /api/v1/notifications} endpoint answers {@code 401}. The API never accepts a
 * recipient id from the client.
 */
@FunctionalInterface
public interface CurrentRecipientProvider {

  /** The fallback used when the project provides no provider: there is never a caller. */
  CurrentRecipientProvider NONE = Optional::empty;

  /**
   * Returns the id of the authenticated caller.
   *
   * @return the caller's recipient id, or empty if the request is not authenticated
   */
  Optional<UUID> currentRecipientId();
}
