package {{ base_package }}.common.config;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.boot.context.properties.bind.Bindable;
import org.springframework.boot.context.properties.bind.Binder;
import org.springframework.boot.context.properties.bind.PropertySourcesPlaceholdersResolver;
import org.springframework.boot.context.properties.source.ConfigurationPropertySources;
import org.springframework.boot.env.YamlPropertySourceLoader;
import org.springframework.core.env.MutablePropertySources;
import org.springframework.core.env.PropertySource;
import org.springframework.core.io.ClassPathResource;

/**
 * Pins the monitoring-related management settings in {@code application.yml} / {@code
 * application-prod.yml} without starting an application context or a database: metrics on a
 * separate port, probes enabled, the Prometheus endpoint exposed, low-cardinality tags and
 * histogram buckets for HTTP latency.
 */
class ManagementConfigTest {

  private static Binder binderFor(String... files) throws IOException {
    MutablePropertySources sources = new MutablePropertySources();
    for (String file : files) {
      List<PropertySource<?>> loaded =
          new YamlPropertySourceLoader().load(file, new ClassPathResource(file));
      loaded.forEach(sources::addLast);
    }
    return new Binder(
        ConfigurationPropertySources.from(sources),
        new PropertySourcesPlaceholdersResolver(sources));
  }

  @Test
  void metricsAreServedOnASeparateManagementPort() throws IOException {
    Binder binder = binderFor("application.yml");

    assertThat(binder.bind("management.server.port", Integer.class).get()).isEqualTo(8081);
  }

  @Test
  void prometheusHealthAndInfoEndpointsAreExposedAndNothingElse() throws IOException {
    Binder binder = binderFor("application.yml");

    List<String> exposed =
        binder
            .bind("management.endpoints.web.exposure.include", Bindable.listOf(String.class))
            .get();

    assertThat(exposed).containsExactlyInAnyOrder("health", "info", "prometheus");
  }

  @Test
  void livenessAndReadinessProbesAreEnabled() throws IOException {
    Binder binder = binderFor("application.yml");

    assertThat(binder.bind("management.endpoint.health.probes.enabled", Boolean.class).get())
        .isTrue();
  }

  @Test
  void metricsCarryOnlyBoundedApplicationAndEnvironmentTags() throws IOException {
    Binder binder = binderFor("application.yml");

    Map<String, String> tags =
        binder.bind("management.metrics.tags", Bindable.mapOf(String.class, String.class)).get();

    assertThat(tags).containsOnlyKeys("application", "environment");
    assertThat(tags.get("environment")).isEqualTo("development");
  }

  @Test
  void prodProfileTagsMetricsWithTheProductionEnvironmentByDefault() throws IOException {
    Binder binder = binderFor("application-prod.yml", "application.yml");

    assertThat(binder.bind("management.metrics.tags.environment", String.class).get())
        .isEqualTo("production");
  }

  @Test
  void httpServerLatencyPublishesHistogramBuckets() throws IOException {
    Binder binder = binderFor("application.yml");

    Map<String, Boolean> histograms =
        binder
            .bind(
                "management.metrics.distribution.percentiles-histogram",
                Bindable.mapOf(String.class, Boolean.class))
            .get();

    assertThat(histograms).containsEntry("http.server.requests", true);
  }
}
