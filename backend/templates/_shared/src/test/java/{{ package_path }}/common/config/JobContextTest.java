package {{ base_package }}.common.config;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;

class JobContextTest {

  @AfterEach
  void cleanMdc() {
    MDC.clear();
  }

  @Test
  void run_putsJobNameAndFreshRequestIdInMdcWhileTheTaskRuns() {
    AtomicReference<String> job = new AtomicReference<>();
    AtomicReference<String> requestId = new AtomicReference<>();

    JobContext.run(
        "orders.cleanup",
        () -> {
          job.set(MDC.get(JobContext.JOB_KEY));
          requestId.set(MDC.get(CorrelationIdFilter.MDC_KEY));
        });

    assertThat(job.get()).isEqualTo("orders.cleanup");
    assertThat(requestId.get()).isNotBlank();
  }

  @Test
  void run_removesBothKeysAfterNormalCompletion() {
    JobContext.run("orders.cleanup", () -> {});

    assertThat(MDC.get(JobContext.JOB_KEY)).isNull();
    assertThat(MDC.get(CorrelationIdFilter.MDC_KEY)).isNull();
  }

  @Test
  void run_removesBothKeysAndRethrowsTheSameExceptionWhenTheTaskThrows() {
    IllegalStateException failure = new IllegalStateException("job failed");

    assertThatThrownBy(
            () ->
                JobContext.run(
                    "orders.cleanup",
                    () -> {
                      throw failure;
                    }))
        .isSameAs(failure);

    assertThat(MDC.get(JobContext.JOB_KEY)).isNull();
    assertThat(MDC.get(CorrelationIdFilter.MDC_KEY)).isNull();
  }

  @Test
  void run_givesEachRunItsOwnRequestId() {
    AtomicReference<String> first = new AtomicReference<>();
    AtomicReference<String> second = new AtomicReference<>();

    JobContext.run("job", () -> first.set(MDC.get(CorrelationIdFilter.MDC_KEY)));
    JobContext.run("job", () -> second.set(MDC.get(CorrelationIdFilter.MDC_KEY)));

    assertThat(first.get()).isNotEqualTo(second.get());
  }

  @Test
  void run_leavesUnrelatedMdcKeysUntouched() {
    MDC.put("tenant", "acme");

    JobContext.run("job", () -> assertThat(MDC.get("tenant")).isEqualTo("acme"));

    assertThat(MDC.get("tenant")).isEqualTo("acme");
  }
}
