package {{ base_package }}.common.config;

import java.util.UUID;
import org.slf4j.MDC;

/**
 * Gives a scheduled run the same log correlation a web request gets from {@link
 * CorrelationIdFilter}. Scheduled methods run on scheduler threads that never pass through the
 * servlet filter, so without this their log lines carry no id at all.
 *
 * <p>While the task runs, MDC holds {@value #JOB_KEY} (the stable job name) and {@link
 * CorrelationIdFilter#MDC_KEY} (a fresh id for this run, so one run's lines can be grouped). Both
 * are removed afterwards so a pooled thread never leaks them into its next run.
 */
public final class JobContext {

  /** MDC key holding the stable job name. */
  public static final String JOB_KEY = "job";

  private JobContext() {}

  /**
   * Runs {@code task} with job context in MDC.
   *
   * @param job the stable job name, for example {@code orders.cleanup}
   * @param task the work; any exception propagates unchanged
   */
  public static void run(String job, Runnable task) {
    MDC.put(JOB_KEY, job);
    MDC.put(CorrelationIdFilter.MDC_KEY, UUID.randomUUID().toString());
    try {
      task.run();
    } finally {
      MDC.remove(CorrelationIdFilter.MDC_KEY);
      MDC.remove(JOB_KEY);
    }
  }
}
