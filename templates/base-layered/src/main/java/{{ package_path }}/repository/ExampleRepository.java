package {{ base_package }}.repository;

import {{ base_package }}.entity.Example;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ExampleRepository extends JpaRepository<Example, Long> {
}
