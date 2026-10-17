package {{ base_package }}.notification;

import {{ base_package }}.common.config.JobContext;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * The outbox worker. Every tick runs three independent steps (a failure in one never blocks the
 * others): promote scheduled notifications that have come due, process due deliveries, and roll
 * final statuses up. Safe to run on several instances: claims use {@code FOR UPDATE SKIP LOCKED}
 * plus a lease.
 *
 * <p>Set {@code app.notifications.worker-enabled=false} to switch it off, for example in test
 * suites that start the full application context against a database.
 */
@Component
@ConditionalOnProperty(
    prefix = "app.notifications",
    name = "worker-enabled",
    havingValue = "true",
    matchIfMissing = true)
@Slf4j
public class DeliveryWorker {

  private final NotificationQueries queries;
  private final DeliveryProcessor processor;
  private final int batchSize;
  private final int leaseSeconds;

  /**
   * Wires the worker; sizes come from {@code app.notifications.*}.
   *
   * @param queries the outbox SQL
   * @param processor sends one claimed delivery
   * @param batchSize the maximum number of deliveries claimed per pass
   * @param leaseSeconds how long a claim is held before another worker may take it over
   */
  public DeliveryWorker(
      NotificationQueries queries,
      DeliveryProcessor processor,
      @Value("${app.notifications.batch-size:100}") int batchSize,
      @Value("${app.notifications.lease-seconds:300}") int leaseSeconds) {
    this.queries = queries;
    this.processor = processor;
    this.batchSize = batchSize;
    this.leaseSeconds = leaseSeconds;
  }

  /** One worker pass; scheduled with a fixed delay so passes never overlap. */
  @Scheduled(fixedDelayString = "${app.notifications.worker-delay-ms:3000}")
  public void tick() {
    JobContext.run(
        "notifications.worker",
        () -> {
          runStep("promoteScheduled", queries::promoteScheduled);
          runStep("processDue", this::processDue);
          runStep("rollUp", queries::rollUp);
        });
  }

  private void runStep(String name, Runnable step) {
    try {
      step.run();
    } catch (RuntimeException e) {
      log.atWarn()
          .addKeyValue("event.name", "notification.worker.step_failed")
          .addKeyValue("worker.step", name)
          .addKeyValue("error.type", e.getClass().getSimpleName())
          .log("Notification worker step failed");
    }
  }

  /** Claims due deliveries and sends them, outside any transaction. */
  void processDue() {
    for (NotificationQueries.DeliveryJob job : queries.claimDue(batchSize, leaseSeconds)) {
      try {
        processor.process(job);
      } catch (RuntimeException e) {
        log.atError()
            .addKeyValue("event.name", "notification.worker.delivery_crashed")
            .addKeyValue("delivery.id", job.id())
            .addKeyValue("error.type", e.getClass().getSimpleName())
            .log("Delivery processing crashed");
      }
    }
  }
}
