package {{ base_package }}.service;

import {{ base_package }}.entity.Example;
import {{ base_package }}.repository.ExampleRepository;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.NoSuchElementException;

@Service
public class ExampleService {

    private final ExampleRepository repository;

    public ExampleService(ExampleRepository repository) {
        this.repository = repository;
    }

    public List<Example> findAll() {
        return repository.findAll();
    }

    public Example findById(Long id) {
        return repository.findById(id)
                .orElseThrow(() -> new NoSuchElementException("Example not found: " + id));
    }

    public Example save(Example example) {
        return repository.save(example);
    }

    public Example update(Long id, Example example) {
        Example existing = findById(id);
        existing.setName(example.getName());
        return repository.save(existing);
    }

    public void delete(Long id) {
        repository.deleteById(id);
    }
}
