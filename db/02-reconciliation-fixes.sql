ALTER TABLE reconciliation_match_items
    ALTER COLUMN settlement_line_id DROP NOT NULL;

ALTER TABLE reconciliation_match_items
    ALTER COLUMN bank_line_id DROP NOT NULL;

ALTER TABLE reconciliation_match_items
    ADD CONSTRAINT chk_match_item_has_source
    CHECK (
        settlement_line_id IS NOT NULL
        OR bank_line_id IS NOT NULL
    );

CREATE TABLE exception_items (
    exception_item_id BIGSERIAL PRIMARY KEY,

    exception_id VARCHAR(30) NOT NULL
        REFERENCES exceptions(exception_id),

    settlement_line_id VARCHAR(40)
        REFERENCES settlement_lines(settlement_line_id),

    bank_line_id VARCHAR(30)
        REFERENCES bank_statement_lines(bank_line_id),

    processor_event_id VARCHAR(40)
        REFERENCES processor_events(event_id),

    delivery_id VARCHAR(40)
        REFERENCES processor_event_deliveries(delivery_id),

    payment_attempt_id VARCHAR(60)
        REFERENCES payment_attempts(attempt_id),

    CHECK (
        num_nonnulls(
            settlement_line_id,
            bank_line_id,
            processor_event_id,
            delivery_id,
            payment_attempt_id
        ) >= 1
    )
);

CREATE INDEX idx_exception_items_exception
    ON exception_items(exception_id);