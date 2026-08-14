-- liquibase formatted sql

-- changeset forge:1700000000000
-- comment: Create the example table
CREATE TABLE example
(
    id   BIGSERIAL PRIMARY KEY,
    name VARCHAR(255)
);

-- rollback DROP TABLE example;
