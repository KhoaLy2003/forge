package {{ base_package }}.common.config;

import {{ base_package }}.common.entity.BaseEntity;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.jpa.repository.config.EnableJpaAuditing;

/**
 * Enables Spring Data JPA auditing so {@code @CreatedDate}/{@code @LastModifiedDate} fields on
 * {@link BaseEntity} are populated automatically by the {@code AuditingEntityListener} on
 * persist/update, without every entity or service needing to set timestamps manually.
 */
@Configuration
@EnableJpaAuditing
public class JpaAuditingConfig {}
