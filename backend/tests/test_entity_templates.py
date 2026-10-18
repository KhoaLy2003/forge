"""Content tests for the entity-driven templates (``templates/_entity`` and ``templates/_join``).

The fixture ``fixtures/entities.forge.yaml`` is rendered once into a real project tree and the generated
text is asserted per relation kind, field type and modifier.
"""

import re
from pathlib import Path

import pytest

from core.config_schema import ForgeConfig
from core.entity_spec import load_forge_yaml
from core.renderer import render_tree, resolve_tree
from core.templates import (
    ENTITY_DIR,
    JOIN_DIR,
    SHARED_DIR,
    SEARCH_PACKAGE_TEMPLATE,
    TEMPLATES_DIR,
    discover_templates,
    dynamic_excludes,
)

FIXTURE = Path(__file__).parent / "fixtures" / "entities.forge.yaml"
PKG = "src/main/java/com/example/demoservice"
TEST_PKG = "src/test/java/com/example/demoservice"
CHANGELOG = "src/main/resources/db/changelog"
JINJA_LEFTOVER = re.compile(r"\{\{|\{%|\{#")

ENTITIES = {
    "Customer": "customer",
    "Order": "order",
    "OrderItem": "orderitem",
    "Product": "product",
    "Category": "category",
}


def _config(target: Path, entities=None, template="base-layered") -> ForgeConfig:
    return ForgeConfig(
        project_name="demo-service",
        target_path=target,
        group_id="com.example",
        artifact_id="demo-service",
        template=template,
        entities=entities if entities is not None else load_forge_yaml(FIXTURE).entities,
    )


def _render(config: ForgeConfig) -> Path:
    context = config.template_context()
    excluded = discover_templates()[config.template] + dynamic_excludes(context)
    render_tree(
        SHARED_DIR,
        config.target_dir,
        context,
        excluded=excluded,
        entities_dir=ENTITY_DIR,
        join_dir=JOIN_DIR,
    )
    return config.target_dir


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> Path:
    return _render(_config(tmp_path_factory.mktemp("entities")))


def read(project: Path, rel: str) -> str:
    return (project / rel).read_text(encoding="utf-8")


def main_file(project: Path, entity: str, layer: str, name: str) -> str:
    return read(project, f"{PKG}/{ENTITIES[entity]}/{layer}/{name}.java")


def test_underscore_template_dirs_exist_and_are_not_templates():
    assert ENTITY_DIR.is_dir() and JOIN_DIR.is_dir()
    assert "_entity" not in discover_templates()
    assert "_join" not in discover_templates()
    assert all(not name.startswith("_") for name in discover_templates())
    assert (TEMPLATES_DIR / "_join").is_dir()


def test_every_entity_gets_its_full_slice(project):
    for name, package in ENTITIES.items():
        main = project / PKG / package
        for rel in (
            f"entity/{name}.java",
            f"repository/{name}Repository.java",
            f"dto/Create{name}Request.java",
            f"dto/Update{name}Request.java",
            f"dto/{name}Response.java",
            f"mapper/{name}Mapper.java",
            f"service/{name}Service.java",
            f"service/{name}ServiceImpl.java",
            f"controller/{name}Controller.java",
        ):
            assert (main / rel).is_file(), rel
        test = project / TEST_PKG / package
        for rel in (
            f"entity/{name}Test.java",
            f"service/{name}ServiceImplTest.java",
            f"mapper/{name}MapperTest.java",
            f"controller/{name}ControllerTest.java",
            f"repository/{name}RepositoryTest.java",
        ):
            assert (test / rel).is_file(), rel


def test_example_slice_and_001_are_absent_when_entities_exist(project):
    assert not (project / PKG / "example").exists()
    assert not (project / TEST_PKG / "example").exists()
    assert not (project / CHANGELOG / "001-create-example-table.sql").exists()
    assert (project / CHANGELOG / "002-create-notifications.sql").is_file()


def test_no_stray_jinja_in_any_generated_entity_file(project):
    checked = 0
    for package in ENTITIES.values():
        for root in (PKG, TEST_PKG):
            for path in (project / root / package).rglob("*.java"):
                assert not JINJA_LEFTOVER.search(path.read_text(encoding="utf-8")), path
                checked += 1
    for path in (project / CHANGELOG).glob("*.sql"):
        if path.name.startswith("002"):
            continue  # the notification seed legitimately contains {{name}} placeholders
        assert not JINJA_LEFTOVER.search(path.read_text(encoding="utf-8")), path
        checked += 1
    assert not JINJA_LEFTOVER.search(read(project, f"{CHANGELOG}/db.changelog-master.xml"))
    assert checked > 40


# ----------------------------------------------------------------------------- entity classes


def test_entity_extends_base_entity_and_declares_table(project):
    text = main_file(project, "Customer", "entity", "Customer")
    assert "package com.example.demoservice.customer.entity;" in text
    assert "public class Customer extends BaseEntity {" in text
    assert re.search(r'@Table\(\s*name = "customers"', text)
    assert "@Entity" in text and "@Getter" in text and "@Setter" in text


def test_reserved_word_entity_uses_explicit_table(project):
    text = main_file(project, "Order", "entity", "Order")
    assert re.search(r'@Table\(\s*name = "customer_orders"', text)
    assert "public class Order extends BaseEntity {" in text


def test_field_columns_carry_length_precision_scale_nullability_and_uniqueness(project):
    customer = main_file(project, "Customer", "entity", "Customer")
    assert '@Column(name = "name", nullable = false, length = 100)' in customer
    assert '@Column(name = "email", nullable = false, length = 150, unique = true)' in customer
    assert '@Column(name = "joined_on")' in customer
    assert '@Column(name = "external_id")' in customer
    assert "private LocalDate joinedOn;" in customer
    assert "private UUID externalId;" in customer
    order = main_file(project, "Order", "entity", "Order")
    assert '@Column(name = "total", nullable = false, precision = 12, scale = 2)' in order
    assert "private BigDecimal total;" in order
    assert '@Column(name = "placed_at", nullable = false)' in order
    assert "private Instant placedAt;" in order
    assert 'columnDefinition = "TEXT"' in order
    product = main_file(project, "Product", "entity", "Product")
    assert "private Long stock = 0L;" in product
    assert "private Boolean available;" in product
    item = main_file(project, "OrderItem", "entity", "OrderItem")
    assert "private Integer quantity = 1;" in item


def test_field_defaults_become_java_initialisers_and_sql_defaults(project):
    customer = main_file(project, "Customer", "entity", "Customer")
    assert re.search(r"@Builder\.Default\s+private Boolean active = true;", customer)
    order = main_file(project, "Order", "entity", "Order")
    assert re.search(r"@Builder\.Default\s+private OrderStatus status = OrderStatus\.NEW;", order)
    orders = sql(project, "005-create-customer_orders-table.sql")
    assert re.search(r"status\s+VARCHAR\(20\)\s+DEFAULT 'NEW',", orders)
    products = sql(project, "006-create-products-table.sql")
    assert re.search(r"stock\s+BIGINT\s+DEFAULT 0,", products)


def test_create_request_does_not_require_fields_that_have_a_default(project):
    create = main_file(project, "Customer", "dto", "CreateCustomerRequest")
    update = main_file(project, "Customer", "dto", "UpdateCustomerRequest")
    assert not re.search(r"@NotNull[^;]*private Boolean active;", create)
    assert re.search(r'@NotNull\(message = "Active is required"\)\s+private Boolean active;', update)


def test_create_mapping_skips_nulls_so_defaults_survive(project):
    text = main_file(project, "Customer", "mapper", "CustomerMapper")
    assert "@BeanMapping(nullValueCheckStrategy = NullValueCheckStrategy.ALWAYS)" in text


def test_enum_is_a_nested_string_enum(project):
    text = main_file(project, "Customer", "entity", "Customer")
    assert "@Enumerated(EnumType.STRING)" in text
    assert '@Column(name = "tier", nullable = false, length = 20)' in text
    assert "private CustomerTier tier;" in text
    assert "public enum CustomerTier {" in text
    assert re.search(r"BRONZE,\s+SILVER,\s+GOLD", text)
    order = main_file(project, "Order", "entity", "Order")
    assert "public enum OrderStatus {" in order


def test_required_many_to_one_is_lazy_and_not_nullable(project):
    text = main_file(project, "Order", "entity", "Order")
    assert "@ManyToOne(fetch = FetchType.LAZY, optional = false)" in text
    assert '@JoinColumn(name = "customer_id", nullable = false)' in text
    assert "private Customer customer;" in text


def test_optional_many_to_one_is_nullable(project):
    text = main_file(project, "Customer", "entity", "Customer")
    assert "@ManyToOne(fetch = FetchType.LAZY)" in text
    assert '@JoinColumn(name = "favorite_product_id")' in text
    assert "private Product favoriteProduct;" in text


def test_one_to_one_is_a_lazy_unique_fk(project):
    text = main_file(project, "Category", "entity", "Category")
    assert "@OneToOne(fetch = FetchType.LAZY)" in text
    assert '@JoinColumn(name = "featured_product_id", unique = true)' in text
    assert "private Product featuredProduct;" in text


def test_many_to_many_owns_a_join_table(project):
    text = main_file(project, "Product", "entity", "Product")
    assert "@ManyToMany(fetch = FetchType.LAZY)" in text
    assert "@JoinTable(" in text
    assert 'name = "categories_products"' in text
    assert 'joinColumns = @JoinColumn(name = "product_id")' in text
    assert 'inverseJoinColumns = @JoinColumn(name = "category_id")' in text
    assert "private Set<Category> categories = new HashSet<>();" in text
    category = main_file(project, "Category", "entity", "Category")
    assert "@ManyToMany" not in category and "@JoinTable" not in category


def test_inverse_one_to_many_has_sync_helpers_only_for_bidirectional_pairs(project):
    customer = main_file(project, "Customer", "entity", "Customer")
    assert '@OneToMany(mappedBy = "customer", fetch = FetchType.LAZY)' in customer
    assert "private List<Order> orders = new ArrayList<>();" in customer
    assert "public void addOrder(Order child) {" in customer
    assert "child.setCustomer(this);" in customer
    assert "public void removeOrder(Order child) {" in customer
    assert "child.setCustomer(null);" in customer
    assert "cascade" not in customer and "orphanRemoval" not in customer


def test_cascade_and_orphan_removal_only_where_the_model_says_so(project):
    order = main_file(project, "Order", "entity", "Order")
    assert "cascade = CascadeType.ALL" in order
    assert "orphanRemoval = true" in order
    assert 'mappedBy = "order"' in order
    for name in ("Customer", "OrderItem", "Product", "Category"):
        text = main_file(project, name, "entity", name)
        assert "CascadeType" not in text, name
        assert "orphanRemoval" not in text, name


def test_unidirectional_one_to_many_is_a_plain_fk_on_the_child(project):
    customer = main_file(project, "Customer", "entity", "Customer")
    assert "ishlist" not in customer  # the parent gets no collection for a unidirectional one-to-many
    assert "List<Product>" not in customer
    product = main_file(project, "Product", "entity", "Product")
    assert '@JoinColumn(name = "customer_id")' in product
    assert "private Customer customer;" in product
    assert "addProduct" not in customer


def test_entity_has_id_based_equals_and_hashcode(project):
    text = main_file(project, "Customer", "entity", "Customer")
    assert "if (!(o instanceof Customer other)) return false;" in text
    assert "return getId() != null && getId().equals(other.getId());" in text
    assert "return getClass().hashCode();" in text


def test_entity_imports_only_what_it_uses(project):
    category = main_file(project, "Category", "entity", "Category")
    assert "import java.util.List;" not in category
    assert "import java.util.Set;" not in category
    assert "import java.math.BigDecimal;" not in category
    order = main_file(project, "Order", "entity", "Order")
    assert "import java.math.BigDecimal;" in order
    assert "import java.time.Instant;" in order
    assert "import java.util.ArrayList;" in order


# ----------------------------------------------------------------------------- repository


def test_repository_uses_soft_delete_finders_and_unique_exists_checks(project):
    text = main_file(project, "Customer", "repository", "CustomerRepository")
    assert "extends JpaRepository<Customer, UUID>, JpaSpecificationExecutor<Customer> {" in text
    assert "Optional<Customer> findByIdAndDeletedAtIsNull(UUID id);" in text
    assert "boolean existsByEmailAndDeletedAtIsNull(String email);" in text
    assert "existsByName" not in text  # name is not unique
    product = main_file(project, "Product", "repository", "ProductRepository")
    assert "boolean existsBySkuAndDeletedAtIsNull(String sku);" in product
    item = main_file(project, "OrderItem", "repository", "OrderItemRepository")
    assert "existsBy" not in item


def test_repository_lists_through_specifications_not_a_page_finder(project):
    text = main_file(project, "Customer", "repository", "CustomerRepository")
    assert "JpaSpecificationExecutor<Customer>" in text
    assert "findAllByDeletedAtIsNull" not in text


def test_filter_record_has_one_component_per_filterable_field_and_to_one_relation(project):
    customer = main_file(project, "Customer", "dto", "CustomerFilter")
    for component in (
        "String name,",
        "Boolean active,",
        "@DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate joinedOnFrom,",
        "@DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate joinedOnTo,",
        "CustomerTier tier,",
        "UUID favoriteProductId) {",
    ):
        assert component in customer
    assert 'SearchSpecifications.idEquals("favoriteProduct", favoriteProductId)' in customer
    order = main_file(project, "Order", "dto", "OrderFilter")
    assert "BigDecimal totalFrom," in order and "BigDecimal totalTo," in order
    assert "Instant placedAtFrom," in order  # Instant binds ISO-8601 without an annotation
    assert 'SearchSpecifications.atMost("total", totalTo)' in order
    assert "@DateTimeFormat" not in order


def test_filter_record_skips_many_to_many_relations(project):
    product = main_file(project, "Product", "dto", "ProductFilter")
    assert "categor" not in product


def test_filter_component_clashing_with_a_list_parameter_gets_a_prefix():
    from core.entity_rules import resolve_model
    from core.entity_spec import EntitySpec, FieldSpec

    entity = EntitySpec(
        name="Shirt",
        table=None,
        fields={"size": FieldSpec(type="string"), "page": FieldSpec(type="int")},
        relations={},
    )
    names = [p.name for p in resolve_model({"Shirt": entity}).entities[0].filters]
    assert names == ["filterSize", "pageFrom", "pageTo"]


def test_repository_checks_one_to_one_target_is_free(project):
    text = main_file(project, "Category", "repository", "CategoryRepository")
    assert "boolean existsByFeaturedProductIdAndDeletedAtIsNull(UUID featuredProductId);" in text


# ----------------------------------------------------------------------------- DTOs


def test_create_request_validates_fields_and_exposes_relation_ids(project):
    text = main_file(project, "Customer", "dto", "CreateCustomerRequest")
    assert "@NotBlank(" in text and "@Size(max = 100" in text
    assert "private String name;" in text
    assert "private CustomerTier tier;" in text
    assert "@NotNull(" in text
    assert "import com.example.demoservice.customer.entity.Customer.CustomerTier;" in text
    assert "private UUID favoriteProductId;" in text
    order = main_file(project, "Order", "dto", "CreateOrderRequest")
    assert "private UUID customerId;" in order
    assert re.search(r'@NotNull\(message = "[^"]*"\)\s+private UUID customerId;', order)
    assert re.search(r"@Digits\(\s*integer = 10,\s+fraction = 2", order)
    product = main_file(project, "Product", "dto", "CreateProductRequest")
    assert "private Set<UUID> categoryIds;" in product
    assert "private UUID lastBuyerId;" in product


def test_requests_and_responses_never_expose_nested_entities(project):
    for name in ENTITIES:
        for dto in (f"Create{name}Request", f"Update{name}Request", f"{name}Response"):
            text = main_file(project, name, "dto", dto)
            assert ".entity.%s;" % name not in text, dto
            assert re.search(r"private (Customer|Order|OrderItem|Product|Category) ", text) is None, dto


def test_update_request_mirrors_create_request(project):
    text = main_file(project, "Order", "dto", "UpdateOrderRequest")
    assert "public class UpdateOrderRequest {" in text
    assert "private UUID customerId;" in text
    assert re.search(r"@Digits\(\s*integer = 10,\s+fraction = 2", text)


def test_response_has_audit_fields_version_and_relation_ids(project):
    text = main_file(project, "Order", "dto", "OrderResponse")
    for expected in (
        "private UUID id;",
        "private String number;",
        "private BigDecimal total;",
        "private UUID customerId;",
        "private Instant createdAt;",
        "private Instant updatedAt;",
        "private Long version;",
    ):
        assert expected in text
    assert "Validated" not in text and "@NotNull" not in text
    product = main_file(project, "Product", "dto", "ProductResponse")
    assert "private Set<UUID> categoryIds;" in product
    assert "private UUID lastBuyerId;" in product


# ----------------------------------------------------------------------------- mapper


def test_mapper_maps_relation_ids_and_ignores_server_managed_fields(project):
    text = main_file(project, "Order", "mapper", "OrderMapper")
    assert '@Mapper(componentModel = "spring", unmappedTargetPolicy = ReportingPolicy.IGNORE)' in text
    assert "public interface OrderMapper {" in text
    assert "Order toEntity(CreateOrderRequest request);" in text
    assert "OrderResponse toResponse(Order entity);" in text
    assert "void updateEntityFromRequest(UpdateOrderRequest request, @MappingTarget Order entity);" in text
    assert '@Mapping(target = "customerId", source = "customer.id")' in text
    assert '@Mapping(target = "customer", ignore = true)' in text
    for server_managed in ("id", "createdAt", "updatedAt", "version", "deletedAt"):
        assert f'@Mapping(target = "{server_managed}", ignore = true)' in text


def test_mapper_converts_many_to_many_entities_to_ids(project):
    text = main_file(project, "Product", "mapper", "ProductMapper")
    assert '@Mapping(target = "categoryIds", expression = "java(ids(entity.getCategories()))")' in text
    assert "default Set<UUID> ids(" in text
    plain = main_file(project, "Category", "mapper", "CategoryMapper")
    assert "default Set<UUID> ids(" not in plain


# ----------------------------------------------------------------------------- service


def test_service_interface_declares_crud_operations(project):
    text = main_file(project, "Customer", "service", "CustomerService")
    for signature in (
        "CustomerResponse findById(UUID id);",
        "PageResponse<CustomerResponse> findAll(",
        "String sortDirection, CustomerFilter filter);",
        "CustomerResponse create(CreateCustomerRequest request);",
        "CustomerResponse update(UUID id, UpdateCustomerRequest request);",
        "void delete(UUID id);",
    ):
        assert signature in text


def test_service_impl_follows_transaction_and_soft_delete_conventions(project):
    text = main_file(project, "Customer", "service", "CustomerServiceImpl")
    assert "@Transactional(readOnly = true)\npublic class CustomerServiceImpl implements CustomerService {" in text
    assert "@Service" in text and "@RequiredArgsConstructor" in text and "@Slf4j" in text
    assert "private final CustomerRepository repository;" in text
    assert "private final CustomerMapper mapper;" in text
    assert "entity.softDelete();" in text
    assert "findByIdAndDeletedAtIsNull" in text
    assert "ResourceNotFoundException" in text
    assert "PaginationUtils.createPageable(page, size, sortBy, sortDirection)" in text


def test_service_checks_unique_fields_and_raises_conflict(project):
    text = main_file(project, "Customer", "service", "CustomerServiceImpl")
    assert "ConflictException" in text
    assert "existsByEmailAndDeletedAtIsNull" in text
    assert "existsByName" not in text
    item = main_file(project, "OrderItem", "service", "OrderItemServiceImpl")
    assert "ConflictException" not in item


def test_service_resolves_each_owning_relation_through_the_target_repository(project):
    order = main_file(project, "Order", "service", "OrderServiceImpl")
    assert "private final CustomerRepository customerRepository;" in order
    assert "customerRepository.findByIdAndDeletedAtIsNull" in order
    assert "setCustomer(" in order
    item = main_file(project, "OrderItem", "service", "OrderItemServiceImpl")
    assert "private final OrderRepository orderRepository;" in item
    assert "private final ProductRepository productRepository;" in item
    product = main_file(project, "Product", "service", "ProductServiceImpl")
    assert "private final CategoryRepository categoryRepository;" in product
    assert "private final CustomerRepository customerRepository;" in product
    assert product.count("private final CustomerRepository") == 1  # two relations, one lookup repository
    assert "setCategories(" in product
    assert "getCategoryIds()" in product


def test_service_does_not_inject_unneeded_repositories(project):
    category = main_file(project, "Category", "service", "CategoryServiceImpl")
    assert "private final ProductRepository productRepository;" in category
    assert "CustomerRepository" not in category


def test_one_to_one_conflict_when_target_already_taken(project):
    text = main_file(project, "Category", "service", "CategoryServiceImpl")
    assert "existsByFeaturedProductIdAndDeletedAtIsNull" in text
    assert "ConflictException" in text


# ----------------------------------------------------------------------------- controller


def test_controller_routes_and_envelope(project):
    text = main_file(project, "OrderItem", "controller", "OrderItemController")
    assert '@RequestMapping("/api/v1/order-items")' in text
    assert "public class OrderItemController {" in text
    assert "private final OrderItemService service;" in text
    assert "ServletUriComponentsBuilder.fromCurrentRequest()" in text
    assert "ResponseEntity.created(location)" in text
    assert "ResponseEntity.noContent().build()" in text
    assert "@Valid @RequestBody CreateOrderItemRequest request" in text
    customer = main_file(project, "Customer", "controller", "CustomerController")
    assert '@RequestMapping("/api/v1/customers")' in customer
    category = main_file(project, "Category", "controller", "CategoryController")
    assert '@RequestMapping("/api/v1/categories")' in category


# ----------------------------------------------------------------------------- generated tests


def test_generated_tests_reference_the_entity_classes(project):
    for name, package in ENTITIES.items():
        service_test = read(project, f"{TEST_PKG}/{package}/service/{name}ServiceImplTest.java")
        assert f"class {name}ServiceImplTest {{" in service_test
        assert f"@InjectMocks private {name}ServiceImpl service;" in service_test
        assert "@ExtendWith(MockitoExtension.class)" in service_test
        mapper_test = read(project, f"{TEST_PKG}/{package}/mapper/{name}MapperTest.java")
        assert f"new {name}MapperImpl()" in mapper_test
        controller_test = read(project, f"{TEST_PKG}/{package}/controller/{name}ControllerTest.java")
        assert f"@WebMvcTest({name}Controller.class)" in controller_test
        assert "@MockitoBean" in controller_test
        repo_test = read(project, f"{TEST_PKG}/{package}/repository/{name}RepositoryTest.java")
        assert "@Testcontainers" in repo_test and "PostgreSQLContainer" in repo_test
        assert f"{name}Repository" in repo_test
        entity_test = read(project, f"{TEST_PKG}/{package}/entity/{name}Test.java")
        assert f"class {name}Test {{" in entity_test


def test_service_test_covers_conflict_and_missing_relation(project):
    text = read(project, f"{TEST_PKG}/customer/service/CustomerServiceImplTest.java")
    assert "ConflictException.class" in text
    assert "existsByEmailAndDeletedAtIsNull" in text
    order = read(project, f"{TEST_PKG}/order/service/OrderServiceImplTest.java")
    assert "@Mock private CustomerRepository customerRepository;" in order
    assert "ResourceNotFoundException.class" in order


def test_repository_test_builds_required_parents_through_their_repositories(project):
    text = read(project, f"{TEST_PKG}/orderitem/repository/OrderItemRepositoryTest.java")
    assert "@Autowired OrderRepository orderRepository;" in text
    assert "@Autowired ProductRepository productRepository;" in text
    assert "@Autowired CustomerRepository customerRepository;" in text  # transitive: Order -> Customer
    assert "@Import(JpaAuditingConfig.class)" in text


def test_sample_values_come_from_the_resolved_fields(project):
    text = read(project, f"{TEST_PKG}/order/service/OrderServiceImplTest.java")
    assert 'new BigDecimal("1.00")' in text
    assert 'Instant.parse("2026-01-01T00:00:00Z")' in text


# ----------------------------------------------------------------------------- Liquibase


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def sql(project: Path, name: str) -> str:
    return read(project, f"{CHANGELOG}/{name}")


def test_changelog_files_are_numbered_in_dependency_order(project):
    names = sorted(p.name for p in (project / CHANGELOG).glob("*.sql"))
    assert names == [
        "002-create-notifications.sql",
        "003-create-categories-table.sql",
        "004-create-customers-table.sql",
        "005-create-customer_orders-table.sql",
        "006-create-products-table.sql",
        "007-create-order_items-table.sql",
        "008-create-categories_products-table.sql",
        "009-add-constraints.sql",
    ]


def test_master_changelog_lists_files_in_order(project):
    text = read(project, f"{CHANGELOG}/db.changelog-master.xml")
    includes = re.findall(r'<include file="db/changelog/([^"]+)" relativeToChangelogFile="false"/>', text)
    assert includes == [
        "002-create-notifications.sql",
        "003-create-categories-table.sql",
        "004-create-customers-table.sql",
        "005-create-customer_orders-table.sql",
        "006-create-products-table.sql",
        "007-create-order_items-table.sql",
        "008-create-categories_products-table.sql",
        "009-add-constraints.sql",
    ]
    assert "001-create-example-table.sql" not in text


def test_table_file_has_columns_audit_columns_and_rollback(project):
    text = sql(project, "004-create-customers-table.sql")
    assert text.startswith("-- liquibase formatted sql\n")
    assert "-- changeset forge:1700000000004" in text
    assert "CREATE TABLE customers" in text
    assert re.search(r"name\s+VARCHAR\(100\)\s+NOT NULL,", text)
    assert re.search(r"email\s+VARCHAR\(150\)\s+NOT NULL,", text)
    assert re.search(r"active\s+BOOLEAN\s+NOT NULL DEFAULT TRUE,", text)
    assert re.search(r"joined_on\s+DATE,", text)
    assert re.search(r"external_id\s+UUID,", text)
    assert re.search(r"tier\s+VARCHAR\(20\)\s+NOT NULL,", text)
    assert re.search(r"version\s+BIGINT\s+NOT NULL DEFAULT 0,", text)
    assert re.search(r"created_at\s+TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,", text)
    assert re.search(r"deleted_at\s+TIMESTAMP WITH TIME ZONE\n\);", text)
    assert re.search(r"id\s+UUID PRIMARY KEY DEFAULT gen_random_uuid\(\),", text)
    assert "-- rollback DROP TABLE customers;" in text


def test_unique_fields_get_named_unique_indexes_over_live_rows(project):
    text = sql(project, "004-create-customers-table.sql")
    assert "CREATE UNIQUE INDEX uq_customers_email ON customers (email) WHERE deleted_at IS NULL;" in text
    assert "uq_customers_name" not in text
    products = sql(project, "006-create-products-table.sql")
    assert "uq_products_sku" in products


def test_required_foreign_key_is_inline_not_null_and_restrict(project):
    text = sql(project, "005-create-customer_orders-table.sql")
    assert re.search(r"customer_id\s+UUID\s+NOT NULL,", text)
    assert "FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE RESTRICT" in flat(text)
    assert "CONSTRAINT fk_customer_orders_customer_id" in text
    assert "CREATE INDEX idx_customer_orders_customer_id ON customer_orders (customer_id);" in text
    assert "CREATE TABLE customer_orders" in text
    assert "-- rollback DROP TABLE customer_orders;" in text
    assert re.search(r"total\s+NUMERIC\(12,2\)\s+NOT NULL,", text)
    assert re.search(r"note\s+TEXT,", text)
    assert re.search(r"placed_at\s+TIMESTAMP WITH TIME ZONE NOT NULL,", text)


def test_two_required_foreign_keys_in_one_table(project):
    text = sql(project, "007-create-order_items-table.sql")
    assert text.count("ON DELETE RESTRICT") == 2
    assert "REFERENCES customer_orders (id)" in text
    assert "REFERENCES products (id)" in text
    assert re.search(r"quantity\s+INTEGER\s+NOT NULL DEFAULT 1,", text)
    assert re.search(r"unit_price\s+NUMERIC\(10,2\)\s+NOT NULL,", text)


def test_optional_foreign_key_column_is_nullable_and_deferred(project):
    customers = sql(project, "004-create-customers-table.sql")
    assert re.search(r"favorite_product_id\s+UUID,", customers)
    assert "REFERENCES products" not in customers
    products = sql(project, "006-create-products-table.sql")
    assert re.search(r"last_buyer_id\s+UUID,", products)
    assert re.search(r"customer_id\s+UUID,", products)  # synthetic FK of the unidirectional one-to-many
    assert "REFERENCES" not in products


def test_one_to_one_foreign_key_gets_a_unique_index_in_its_table_file(project):
    text = sql(project, "003-create-categories-table.sql")
    assert re.search(r"featured_product_id\s+UUID,", text)
    assert (
        "CREATE UNIQUE INDEX uq_categories_featured_product_id ON categories (featured_product_id) "
        "WHERE deleted_at IS NULL;"
    ) in text


def test_constraints_file_adds_deferred_foreign_keys_and_indexes_with_rollback(project):
    text = sql(project, "009-add-constraints.sql")
    assert "-- changeset forge:1700000000009" in text
    assert "ALTER TABLE customers" in text
    assert (
        "ADD CONSTRAINT fk_customers_favorite_product_id FOREIGN KEY (favorite_product_id) "
        "REFERENCES products (id) ON DELETE RESTRICT"
    ) in flat(text)
    assert "ALTER TABLE products" in text
    assert "ADD CONSTRAINT fk_products_last_buyer_id FOREIGN KEY (last_buyer_id)" in text
    assert "ADD CONSTRAINT fk_products_customer_id FOREIGN KEY (customer_id)" in text
    assert "ALTER TABLE categories" in text
    assert "fk_categories_featured_product_id" in text
    assert "CREATE INDEX idx_customers_favorite_product_id ON customers (favorite_product_id);" in text
    assert "CREATE INDEX idx_products_last_buyer_id ON products (last_buyer_id);" in text
    # the one-to-one FK is unique, so no extra plain index
    assert "idx_categories_featured_product_id" not in text
    assert "-- rollback ALTER TABLE customers DROP CONSTRAINT fk_customers_favorite_product_id;" in text
    assert "-- rollback DROP INDEX idx_customers_favorite_product_id;" in text
    assert text.count("ADD CONSTRAINT") == 4
    assert text.count("-- rollback ALTER TABLE") == 4


def test_join_table_has_composite_primary_key_and_both_foreign_keys(project):
    text = sql(project, "008-create-categories_products-table.sql")
    assert "-- changeset forge:1700000000008" in text
    assert "CREATE TABLE categories_products" in text
    assert re.search(r"product_id\s+UUID\s+NOT NULL,", text)
    assert re.search(r"category_id\s+UUID\s+NOT NULL,", text)
    assert "PRIMARY KEY (product_id, category_id)" in text
    assert "FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE RESTRICT" in flat(text)
    assert "FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE RESTRICT" in flat(text)
    assert "CREATE INDEX idx_categories_products_category_id ON categories_products (category_id);" in text
    assert "idx_categories_products_product_id" not in text  # covered by the primary key
    assert "-- rollback DROP TABLE categories_products;" in text


def test_every_changeset_has_a_rollback_and_ids_are_unique(project):
    ids = []
    for path in sorted((project / CHANGELOG).glob("*.sql")):
        text = path.read_text(encoding="utf-8")
        changesets = re.findall(r"^-- changeset (\S+)$", text, flags=re.M)
        assert changesets, path.name
        assert text.count("-- rollback") >= len(changesets), path.name
        ids += changesets
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"forge:17000000000\d\d", i) for i in ids)


def test_sql_files_have_balanced_parentheses(project):
    for path in (project / CHANGELOG).glob("*.sql"):
        text = path.read_text(encoding="utf-8")
        assert text.count("(") == text.count(")"), path.name


# ----------------------------------------------------------------------------- without entities


NO_ENTITY_MASTER = """<?xml version="1.0" encoding="UTF-8"?>
<databaseChangeLog
        xmlns="http://www.liquibase.org/xml/ns/dbchangelog"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://www.liquibase.org/xml/ns/dbchangelog
        http://www.liquibase.org/xml/ns/dbchangelog/dbchangelog-4.0.xsd">

    <include file="db/changelog/001-create-example-table.sql" relativeToChangelogFile="false"/>
    <include file="db/changelog/002-create-notifications.sql" relativeToChangelogFile="false"/>

</databaseChangeLog>
"""


def test_master_changelog_without_entities_is_unchanged(tmp_path):
    config = _config(tmp_path, entities={})
    target = _render(config)
    assert read(target, f"{CHANGELOG}/db.changelog-master.xml") == NO_ENTITY_MASTER
    assert sorted(p.name for p in (target / CHANGELOG).iterdir()) == [
        "001-create-example-table.sql",
        "002-create-notifications.sql",
        "db.changelog-master.xml",
    ]
    assert (target / PKG / "example").is_dir()


def test_no_entities_means_no_entity_or_join_files_at_all(tmp_path):
    config = _config(tmp_path, entities={})
    context = config.template_context()
    with_dirs = resolve_tree(SHARED_DIR, context, entities_dir=ENTITY_DIR, join_dir=JOIN_DIR)
    plain = resolve_tree(SHARED_DIR, context)
    assert with_dirs == plain
    assert not any(p.name.startswith("None") or p.name == "" for p in plain)


def test_minimal_template_gains_no_changelog_files(tmp_path):
    config = _config(tmp_path, entities={}, template="minimal")
    target = _render(config)
    assert not (target / "src/main/resources/db").exists()


def test_constraints_file_only_exists_when_there_are_deferred_foreign_keys(tmp_path):
    entities = load_forge_yaml(FIXTURE).entities
    only_required = {
        "Customer": entities["Customer"].model_copy(update={"relations": {}}),
        "Order": entities["Order"].model_copy(
            update={"relations": {k: v for k, v in entities["Order"].relations.items() if k == "customer"}}
        ),
    }
    config = _config(tmp_path, entities=only_required)
    assert config.template_context()["constraints_changelog_file"] is None
    target = _render(config)
    names = sorted(p.name for p in (target / CHANGELOG).iterdir())
    assert names == [
        "002-create-notifications.sql",
        "003-create-customers-table.sql",
        "004-create-customer_orders-table.sql",
        "db.changelog-master.xml",
    ]
    master = read(target, f"{CHANGELOG}/db.changelog-master.xml")
    assert "add-constraints" not in master


def test_constraints_changelog_file_is_in_the_context(tmp_path):
    context = _config(tmp_path).template_context()
    assert context["constraints_changelog_file"] == "009-add-constraints.sql"
    assert context["changelog_files"][-1] == "009-add-constraints.sql"
    assert _config(tmp_path, entities={}).template_context()["constraints_changelog_file"] is None


def test_constraints_template_name_matches_the_dynamic_exclude_constant():
    from core.templates import CONSTRAINTS_CHANGELOG_TEMPLATE

    assert (SHARED_DIR / CONSTRAINTS_CHANGELOG_TEMPLATE).is_file()
    assert CONSTRAINTS_CHANGELOG_TEMPLATE in dynamic_excludes({"has_entities": True})
    assert CONSTRAINTS_CHANGELOG_TEMPLATE not in dynamic_excludes(
        {"has_entities": True, "constraints_changelog_file": "009-add-constraints.sql"}
    )
    assert dynamic_excludes({"has_entities": False}) == (SEARCH_PACKAGE_TEMPLATE,)
