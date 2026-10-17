package {{ base_package }}.notification;

import java.util.Optional;
import java.util.UUID;

/**
 * Resolves a recipient id to contact details. The generated project has no user model, so recipient
 * ids are opaque to this module; implement this interface as a Spring bean (for example a
 * {@code @Component} backed by your user repository) to enable the email channel. Without a bean,
 * {@link #NONE} is used: nobody resolves, so email deliveries are skipped with the reason {@code
 * recipient_unresolved} while in-app notifications keep working.
 */
@FunctionalInterface
public interface RecipientDirectory {

  /** The fallback used when the project provides no directory: nobody can be resolved. */
  RecipientDirectory NONE = recipientId -> Optional.empty();

  /**
   * Looks a recipient up.
   *
   * @param recipientId the recipient id
   * @return the recipient's details, or empty if unknown (for example a deleted account)
   */
  Optional<Recipient> find(UUID recipientId);
}
