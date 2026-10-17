-- liquibase formatted sql

-- changeset forge:1700000000002
-- comment: Notification module: templates, outbox (notifications + deliveries) and preferences
CREATE TABLE notification_templates
(
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_key     VARCHAR(80)              NOT NULL,
    channel          VARCHAR(10)              NOT NULL,
    locale           VARCHAR(2)               NOT NULL,
    subject          VARCHAR(200)             NOT NULL,
    body             TEXT                     NOT NULL,
    template_version INT                      NOT NULL DEFAULT 1,
    active           BOOLEAN                  NOT NULL DEFAULT TRUE,
    version          BIGINT                   NOT NULL DEFAULT 0,
    created_at       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at       TIMESTAMP WITH TIME ZONE,
    CONSTRAINT chk_notification_templates_channel CHECK (channel IN ('in_app', 'email'))
);

CREATE UNIQUE INDEX uq_notification_templates_key
    ON notification_templates (template_key, channel, locale);

-- The outbox record: one row per send request.
CREATE TABLE notifications
(
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type            VARCHAR(40)              NOT NULL,
    template_key    VARCHAR(80)              NOT NULL,
    channels        VARCHAR(40)              NOT NULL,
    audience_type   VARCHAR(10)              NOT NULL,
    data            JSONB                    NOT NULL DEFAULT '{}'::jsonb,
    status          VARCHAR(20)              NOT NULL,
    scheduled_at    TIMESTAMP WITH TIME ZONE,
    idempotency_key VARCHAR(100),
    created_by      UUID,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_notifications_audience_type CHECK (audience_type IN ('users'))
);

CREATE UNIQUE INDEX uq_notifications_idempotency_key
    ON notifications (idempotency_key) WHERE idempotency_key IS NOT NULL;
CREATE INDEX idx_notifications_created_at ON notifications (created_at DESC);

-- One row per notification, recipient and channel. recipient_id is deliberately not a foreign key:
-- the project decides what a recipient is (see RecipientDirectory).
CREATE TABLE deliveries
(
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notification_id     UUID                     NOT NULL REFERENCES notifications (id),
    recipient_id        UUID                     NOT NULL,
    channel             VARCHAR(10)              NOT NULL,
    status              VARCHAR(10)              NOT NULL DEFAULT 'pending',
    attempt_count       INT                      NOT NULL DEFAULT 0,
    provider_message_id VARCHAR(255),
    next_retry_at       TIMESTAMP WITH TIME ZONE NOT NULL,
    last_error          VARCHAR(500),
    skip_reason         VARCHAR(30),
    title               VARCHAR(200),
    body                TEXT,
    read_at             TIMESTAMP WITH TIME ZONE,
    dismissed_at        TIMESTAMP WITH TIME ZONE,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_deliveries_channel CHECK (channel IN ('in_app', 'email'))
);

CREATE UNIQUE INDEX uq_deliveries_notification_recipient_channel
    ON deliveries (notification_id, recipient_id, channel);
CREATE INDEX idx_deliveries_due ON deliveries (next_retry_at) WHERE status = 'pending';
CREATE INDEX idx_deliveries_inbox ON deliveries (recipient_id, created_at DESC) WHERE channel = 'in_app';
CREATE INDEX idx_deliveries_notification_status ON deliveries (notification_id, status);

CREATE TABLE notification_preferences
(
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_id  UUID                     NOT NULL UNIQUE,
    email_enabled BOOLEAN                  NOT NULL DEFAULT TRUE,
    version       BIGINT                   NOT NULL DEFAULT 0,
    created_at    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at    TIMESTAMP WITH TIME ZONE
);

-- Seed: one generic example. Add your own templates with further migrations.
INSERT INTO notification_templates (template_key, channel, locale, subject, body)
VALUES ('welcome', 'in_app', 'en', 'Welcome, {% raw %}{{name}}{% endraw %}!',
        'Thanks for joining. We are glad you are here, {% raw %}{{name}}{% endraw %}.'),
       ('welcome', 'email', 'en', 'Welcome, {% raw %}{{name}}{% endraw %}!',
        'Thanks for joining. We are glad you are here, {% raw %}{{name}}{% endraw %}.');

-- rollback DROP TABLE notification_preferences;
-- rollback DROP TABLE deliveries;
-- rollback DROP TABLE notifications;
-- rollback DROP TABLE notification_templates;
