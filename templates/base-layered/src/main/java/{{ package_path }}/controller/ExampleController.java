package {{ base_package }}.controller;

import {{ base_package }}.entity.Example;
import {{ base_package }}.service.ExampleService;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/examples")
public class ExampleController {

    private final ExampleService service;

    public ExampleController(ExampleService service) {
        this.service = service;
    }

    @GetMapping
    public List<Example> findAll() {
        return service.findAll();
    }

    @GetMapping("/{id}")
    public Example findById(@PathVariable Long id) {
        return service.findById(id);
    }

    @PostMapping
    public Example create(@RequestBody Example example) {
        return service.save(example);
    }

    @PutMapping("/{id}")
    public Example update(@PathVariable Long id, @RequestBody Example example) {
        return service.update(id, example);
    }

    @DeleteMapping("/{id}")
    public void delete(@PathVariable Long id) {
        service.delete(id);
    }
}
