package {{ base_package }}.notification;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import {{ base_package }}.common.config.CorrelationIdFilter;
import {{ base_package }}.common.config.JobContext;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.mockito.InOrder;
import org.slf4j.MDC;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.scheduling.annotation.Scheduled;

class DeliveryWorkerTest {

  private final NotificationQueries queries = mock(NotificationQueries.class);
  private final DeliveryProcessor processor = mock(DeliveryProcessor.class);
  private final DeliveryWorker worker = new DeliveryWorker(queries, processor, 25, 120);

  @AfterEach
  void cleanMdc() {
    MDC.clear();
  }

  private static NotificationQueries.DeliveryJob job() {
    return new NotificationQueries.DeliveryJob(
        UUID.randomUUID(), UUID.randomUUID(), UUID.randomUUID(), "in_app", 0);
  }

  @Test
  void tick_runsPromoteThenProcessThenRollUpInOrder() {
    when(queries.claimDue(25, 120)).thenReturn(List.of());

    worker.tick();

    InOrder order = inOrder(queries);
    order.verify(queries).promoteScheduled();
    order.verify(queries).claimDue(25, 120);
    order.verify(queries).rollUp();
  }

  @Test
  void tick_passesTheConfiguredBatchSizeAndLeaseToTheClaim() {
    when(queries.claimDue(25, 120)).thenReturn(List.of());

    worker.tick();

    verify(queries).claimDue(25, 120);
  }

  @Test
  void tick_processesEveryClaimedDelivery() {
    NotificationQueries.DeliveryJob first = job();
    NotificationQueries.DeliveryJob second = job();
    when(queries.claimDue(25, 120)).thenReturn(List.of(first, second));

    worker.tick();

    verify(processor).process(first);
    verify(processor).process(second);
  }

  @Test
  void tick_withNothingDue_neverCallsTheProcessor() {
    when(queries.claimDue(25, 120)).thenReturn(List.of());

    worker.tick();

    verify(processor, never()).process(any());
  }

  @Test
  void aStepThatThrowsDoesNotStopTheLaterSteps() {
    when(queries.promoteScheduled()).thenThrow(new IllegalStateException("db hiccup"));
    when(queries.claimDue(25, 120)).thenReturn(List.of());

    worker.tick();

    verify(queries).claimDue(25, 120);
    verify(queries).rollUp();
  }

  @Test
  void aFailingProcessStepDoesNotPreventTheRollUp() {
    when(queries.claimDue(25, 120)).thenThrow(new IllegalStateException("db gone"));

    worker.tick();

    verify(queries).rollUp();
  }

  @Test
  void aDeliveryThatThrowsDoesNotStopTheRestOfTheBatch() {
    NotificationQueries.DeliveryJob bad = job();
    NotificationQueries.DeliveryJob good = job();
    when(queries.claimDue(25, 120)).thenReturn(List.of(bad, good));
    doThrow(new IllegalStateException("unexpected")).when(processor).process(bad);

    worker.tick();

    verify(processor).process(good);
    verify(queries).rollUp();
  }

  @Test
  void tick_runsInsideAJobContextAndCleansUpAfterwards() {
    AtomicReference<String> job = new AtomicReference<>();
    AtomicReference<String> requestId = new AtomicReference<>();
    when(queries.promoteScheduled())
        .thenAnswer(
            call -> {
              job.set(MDC.get(JobContext.JOB_KEY));
              requestId.set(MDC.get(CorrelationIdFilter.MDC_KEY));
              return 0;
            });
    when(queries.claimDue(25, 120)).thenReturn(List.of());

    worker.tick();

    assertThat(job.get()).isEqualTo("notifications.worker");
    assertThat(requestId.get()).isNotBlank();
    assertThat(MDC.get(JobContext.JOB_KEY)).isNull();
    assertThat(MDC.get(CorrelationIdFilter.MDC_KEY)).isNull();
  }

  @Test
  void tick_isScheduledWithAConfigurableFixedDelay() throws NoSuchMethodException {
    Scheduled scheduled = DeliveryWorker.class.getMethod("tick").getAnnotation(Scheduled.class);

    assertThat(scheduled).isNotNull();
    assertThat(scheduled.fixedDelayString()).isEqualTo("${app.notifications.worker-delay-ms:3000}");
  }

  @Test
  void theWorkerBeanExistsByDefaultAndCanBeSwitchedOff() {
    ApplicationContextRunner runner =
        new ApplicationContextRunner()
            .withBean(NotificationQueries.class, () -> queries)
            .withBean(DeliveryProcessor.class, () -> processor)
            .withUserConfiguration(DeliveryWorker.class);

    runner.run(context -> assertThat(context).hasSingleBean(DeliveryWorker.class));
    runner
        .withPropertyValues("app.notifications.worker-enabled=false")
        .run(context -> assertThat(context).doesNotHaveBean(DeliveryWorker.class));
    runner
        .withPropertyValues("app.notifications.worker-enabled=true")
        .run(context -> assertThat(context).hasSingleBean(DeliveryWorker.class));
  }
}
