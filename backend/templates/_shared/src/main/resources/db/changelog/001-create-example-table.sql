-- liquibase formatted sql

-- changeset forge:1700000000000
-- comment: Create the example table
CREATE TABLE example
(
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name       VARCHAR(120)             NOT NULL,
    status     VARCHAR(20)              NOT NULL DEFAULT 'ACTIVE',
    version    BIGINT                   NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_example_status ON example (status);
CREATE INDEX idx_example_deleted_at ON example (deleted_at);

-- rollback DROP TABLE example;
