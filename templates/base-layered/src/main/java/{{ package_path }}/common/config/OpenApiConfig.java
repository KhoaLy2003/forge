package {{ base_package }}.common.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Supplies the base {@link OpenAPI} metadata (title, version, description) rendered by
 * springdoc-openapi's generated {@code /v3/api-docs} and Swagger UI, so the generated project ships
 * with meaningful API documentation out of the box instead of the library's defaults.
 */
@Configuration
public class OpenApiConfig {

  /**
   * Builds the {@link OpenAPI} bean that springdoc-openapi merges with the endpoints it scans to
   * produce the API documentation.
   *
   * @return an {@link OpenAPI} descriptor populated with this project's title, version, and
   *     description
   */
  @Bean
  public OpenAPI exampleServiceOpenAPI() {
    return new OpenAPI()
        .info(
            new Info()
                .title("{{ project_name }}")
                .version("0.0.1")
                .description("API documentation for {{ project_name }}"));
  }
}
