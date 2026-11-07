
-- ============================================================
-- PAYMENT RECONCILIATION
-- MIGRATION 03
-- ============================================================

-- 1. Extend bank statement records.

ALTER TABLE bank_statement_lines
    ADD COLUMN IF NOT EXISTS batch_id VARCHAR(30);

ALTER TABLE bank_statement_lines
    ADD COLUMN IF NOT EXISTS bank_name VARCHAR(100);

ALTER TABLE bank_statement_lines
    ADD COLUMN IF NOT EXISTS transaction_type VARCHAR(20);

ALTER TABLE bank_statement_lines
    ADD COLUMN IF NOT EXISTS transaction_timestamp TIMESTAMPTZ;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_bank_line_batch'
    ) THEN
        ALTER TABLE bank_statement_lines
            ADD CONSTRAINT fk_bank_line_batch
            FOREIGN KEY (batch_id)
            REFERENCES settlement_batches(batch_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_bank_transaction_type'
    ) THEN
        ALTER TABLE bank_statement_lines
            ADD CONSTRAINT chk_bank_transaction_type
            CHECK (
                transaction_type IS NULL
                OR transaction_type IN ('CREDIT', 'DEBIT')
            );
    END IF;
END $$;


-- 2. Extend reconciliation matches.

ALTER TABLE reconciliation_matches
    ADD COLUMN IF NOT EXISTS batch_id VARCHAR(30);

ALTER TABLE reconciliation_matches
    ADD COLUMN IF NOT EXISTS bank_line_id VARCHAR(30);

ALTER TABLE reconciliation_matches
    ADD COLUMN IF NOT EXISTS expected_currency CHAR(3);

ALTER TABLE reconciliation_matches
    ADD COLUMN IF NOT EXISTS actual_currency CHAR(3);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_match_batch'
    ) THEN
        ALTER TABLE reconciliation_matches
            ADD CONSTRAINT fk_match_batch
            FOREIGN KEY (batch_id)
            REFERENCES settlement_batches(batch_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_match_bank_line'
    ) THEN
        ALTER TABLE reconciliation_matches
            ADD CONSTRAINT fk_match_bank_line
            FOREIGN KEY (bank_line_id)
            REFERENCES bank_statement_lines(bank_line_id);
    END IF;
END $$;


-- 3. Extend exceptions.

ALTER TABLE exceptions
    ADD COLUMN IF NOT EXISTS batch_id VARCHAR(30);

ALTER TABLE exceptions
    ADD COLUMN IF NOT EXISTS bank_line_id VARCHAR(30);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_exception_batch'
    ) THEN
        ALTER TABLE exceptions
            ADD CONSTRAINT fk_exception_batch
            FOREIGN KEY (batch_id)
            REFERENCES settlement_batches(batch_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_exception_bank_line'
    ) THEN
        ALTER TABLE exceptions
            ADD CONSTRAINT fk_exception_bank_line
            FOREIGN KEY (bank_line_id)
            REFERENCES bank_statement_lines(bank_line_id);
    END IF;
END $$;


-- 4. Add refunds.

CREATE TABLE IF NOT EXISTS refunds (
    refund_id VARCHAR(40) PRIMARY KEY,

    payment_id VARCHAR(30) NOT NULL
        REFERENCES payment_orders(payment_id),

    attempt_id VARCHAR(60) NOT NULL
        REFERENCES payment_attempts(attempt_id),

    merchant_id VARCHAR(30) NOT NULL
        REFERENCES merchants(merchant_id),

    amount_minor BIGINT NOT NULL
        CHECK (amount_minor > 0),

    currency CHAR(3) NOT NULL,

    status VARCHAR(20) NOT NULL
        CHECK (
            status IN (
                'PENDING',
                'PROCESSED',
                'FAILED'
            )
        ),

    refund_timestamp TIMESTAMPTZ NOT NULL
);


-- 5. Add expected settlements.

CREATE TABLE IF NOT EXISTS expected_settlements (
    expected_settlement_id VARCHAR(50) PRIMARY KEY,

    batch_id VARCHAR(30) NOT NULL UNIQUE
        REFERENCES settlement_batches(batch_id),

    merchant_id VARCHAR(30) NOT NULL
        REFERENCES merchants(merchant_id),

    processor_name VARCHAR(50) NOT NULL,

    currency CHAR(3) NOT NULL,

    expected_amount_minor BIGINT NOT NULL,

    expected_date DATE NOT NULL,

    status VARCHAR(20) NOT NULL
        CHECK (
            status IN (
                'DELAYED',
                'MISSING'
            )
        )
);


-- 6. Add separate synthetic ground truth.
-- Operational reconciliation must not use these labels.

CREATE TABLE IF NOT EXISTS synthetic_ground_truth (
    ground_truth_id BIGSERIAL PRIMARY KEY,

    entity_type VARCHAR(40) NOT NULL,

    entity_id VARCHAR(60) NOT NULL,

    label VARCHAR(60) NOT NULL,

    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (entity_type, entity_id, label)
);


-- 7. Extend exception items with source information.

ALTER TABLE exception_items
    ADD COLUMN IF NOT EXISTS external_exception_item_id VARCHAR(40);

ALTER TABLE exception_items
    ADD COLUMN IF NOT EXISTS source_type VARCHAR(30);

CREATE UNIQUE INDEX IF NOT EXISTS
    idx_exception_items_external_id
    ON exception_items(external_exception_item_id)
    WHERE external_exception_item_id IS NOT NULL;


-- 8. Add useful indexes.

CREATE INDEX IF NOT EXISTS
    idx_bank_batch
    ON bank_statement_lines(batch_id);

CREATE INDEX IF NOT EXISTS
    idx_matches_batch
    ON reconciliation_matches(batch_id);

CREATE INDEX IF NOT EXISTS
    idx_matches_bank
    ON reconciliation_matches(bank_line_id);

CREATE INDEX IF NOT EXISTS
    idx_exceptions_batch
    ON exceptions(batch_id);

CREATE INDEX IF NOT EXISTS
    idx_expected_settlement_status
    ON expected_settlements(status);

CREATE INDEX IF NOT EXISTS
    idx_ground_truth_entity
    ON synthetic_ground_truth(entity_type, entity_id);
