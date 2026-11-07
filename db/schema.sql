CREATE TABLE merchants (
    merchant_id VARCHAR(30) PRIMARY KEY,
    merchant_name VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    country VARCHAR(2) NOT NULL,
    default_currency CHAR(3) NOT NULL,
    status VARCHAR(20) NOT NULL
        CHECK (status IN ('ACTIVE', 'INACTIVE', 'SUSPENDED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE payment_orders (
    payment_id VARCHAR(30) PRIMARY KEY,
    merchant_id VARCHAR(30) NOT NULL REFERENCES merchants(merchant_id),
    customer_reference VARCHAR(100),
    amount_minor BIGINT NOT NULL CHECK (amount_minor > 0),
    currency CHAR(3) NOT NULL,
    status VARCHAR(20) NOT NULL
        CHECK (status IN ('CREATED', 'PENDING', 'PAID', 'FAILED', 'REFUNDED', 'PARTIALLY_REFUNDED')),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE payment_attempts (
    attempt_id VARCHAR(60) PRIMARY KEY,
    payment_id VARCHAR(30) NOT NULL REFERENCES payment_orders(payment_id),
    attempt_number SMALLINT NOT NULL CHECK (attempt_number > 0),
    processor_name VARCHAR(50) NOT NULL,
    processor_reference VARCHAR(100) UNIQUE,
    status VARCHAR(20) NOT NULL
        CHECK (status IN ('INITIATED', 'AUTHORIZED', 'CAPTURED', 'FAILED', 'CANCELLED')),
    attempted_at TIMESTAMPTZ NOT NULL,
    captured_at TIMESTAMPTZ,
    UNIQUE (payment_id, attempt_number),
    CHECK (captured_at IS NULL OR captured_at >= attempted_at)
);

CREATE TABLE processor_events (
    event_id VARCHAR(40) PRIMARY KEY,
    attempt_id VARCHAR(60) NOT NULL REFERENCES payment_attempts(attempt_id),
    processor_name VARCHAR(50) NOT NULL,
    external_event_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(30) NOT NULL
        CHECK (event_type IN ('INITIATED', 'AUTHORIZED', 'CAPTURED', 'FAILED', 'REFUNDED')),
    event_status VARCHAR(20) NOT NULL
        CHECK (event_status IN ('RECEIVED', 'PROCESSED', 'REJECTED')),
    event_timestamp TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    UNIQUE (processor_name, external_event_id)
);

-- Every webhook delivery is retained, including duplicate deliveries.
CREATE TABLE processor_event_deliveries (
    delivery_id VARCHAR(40) PRIMARY KEY,
    event_id VARCHAR(40) NOT NULL REFERENCES processor_events(event_id),
    received_at TIMESTAMPTZ NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    is_duplicate BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE settlement_batches (
    batch_id VARCHAR(30) PRIMARY KEY,
    merchant_id VARCHAR(30) NOT NULL REFERENCES merchants(merchant_id),
    processor_name VARCHAR(50) NOT NULL,
    currency CHAR(3) NOT NULL,
    settlement_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL
        CHECK (status IN ('GENERATED', 'SUBMITTED', 'SETTLED', 'DELAYED', 'FAILED')),
    gross_amount_minor BIGINT NOT NULL DEFAULT 0,
    refund_amount_minor BIGINT NOT NULL DEFAULT 0,
    fee_amount_minor BIGINT NOT NULL DEFAULT 0,
    net_amount_minor BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    settled_at TIMESTAMPTZ,
    CHECK (
        net_amount_minor =
        gross_amount_minor - refund_amount_minor - fee_amount_minor
    )
);

CREATE TABLE settlement_lines (
    settlement_line_id VARCHAR(40) PRIMARY KEY,
    batch_id VARCHAR(30) NOT NULL REFERENCES settlement_batches(batch_id),
    attempt_id VARCHAR(60) NOT NULL REFERENCES payment_attempts(attempt_id),
    line_type VARCHAR(20) NOT NULL
        CHECK (line_type IN ('CAPTURE', 'REFUND', 'FEE_ADJUSTMENT')),
    currency CHAR(3) NOT NULL,
    signed_amount_minor BIGINT NOT NULL,
    fee_amount_minor BIGINT NOT NULL DEFAULT 0,
    net_amount_minor BIGINT GENERATED ALWAYS AS
        (signed_amount_minor - fee_amount_minor) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE bank_statement_lines (
    bank_line_id VARCHAR(30) PRIMARY KEY,
    merchant_id VARCHAR(30) NOT NULL REFERENCES merchants(merchant_id),
    bank_reference VARCHAR(100),
    bank_account_reference VARCHAR(100) NOT NULL,
    transaction_date DATE NOT NULL,
    value_date DATE,
    currency CHAR(3) NOT NULL,
    amount_minor BIGINT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (value_date IS NULL OR value_date >= transaction_date)
);

CREATE TABLE reconciliation_matches (
    match_id VARCHAR(30) PRIMARY KEY,
    merchant_id VARCHAR(30) NOT NULL REFERENCES merchants(merchant_id),
    status VARCHAR(20) NOT NULL
        CHECK (status IN ('MATCHED', 'PARTIAL', 'UNMATCHED', 'REJECTED')),
    matching_method VARCHAR(30) NOT NULL,
    expected_amount_minor BIGINT NOT NULL,
    actual_amount_minor BIGINT NOT NULL,
    variance_minor BIGINT NOT NULL,
    currency CHAR(3) NOT NULL,
    confidence_score NUMERIC(5,4)
        CHECK (confidence_score BETWEEN 0 AND 1),
    matched_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Supports many-to-many reconciliation.
CREATE TABLE reconciliation_match_items (
    match_item_id BIGSERIAL PRIMARY KEY,
    match_id VARCHAR(30) NOT NULL REFERENCES reconciliation_matches(match_id),
    settlement_line_id VARCHAR(40) NOT NULL REFERENCES settlement_lines(settlement_line_id),
    bank_line_id VARCHAR(30) NOT NULL REFERENCES bank_statement_lines(bank_line_id),
    allocated_amount_minor BIGINT NOT NULL,
    UNIQUE (match_id, settlement_line_id, bank_line_id)
);

CREATE TABLE exceptions (
    exception_id VARCHAR(30) PRIMARY KEY,
    merchant_id VARCHAR(30) NOT NULL REFERENCES merchants(merchant_id),
    match_id VARCHAR(30) REFERENCES reconciliation_matches(match_id),
    issue_type VARCHAR(40) NOT NULL
        CHECK (issue_type IN (
            'AMOUNT_MISMATCH',
            'DUPLICATE_SETTLEMENT_LINE',
            'DUPLICATE_PROCESSOR_EVENT',
            'UNMATCHED_SETTLEMENT',
            'UNMATCHED_BANK',
            'CURRENCY_MISMATCH',
            'DELAYED_SETTLEMENT',
            'OUT_OF_ORDER_EVENT',
            'MISSING_RECORD'
        )),
    severity VARCHAR(20) NOT NULL
        CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    status VARCHAR(20) NOT NULL
        CHECK (status IN ('OPEN', 'INVESTIGATING', 'RESOLVED', 'REJECTED')),
    description TEXT NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE TABLE resolutions (
    resolution_id VARCHAR(30) PRIMARY KEY,
    exception_id VARCHAR(30) NOT NULL REFERENCES exceptions(exception_id),
    resolved_by VARCHAR(100) NOT NULL,
    resolution_type VARCHAR(40) NOT NULL,
    notes TEXT NOT NULL,
    previous_status VARCHAR(20) NOT NULL,
    new_status VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Immutable audit history for important business actions.
CREATE TABLE audit_events (
    audit_id BIGSERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    old_state JSONB,
    new_state JSONB,
    actor VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for common reconciliation queries.
CREATE INDEX idx_orders_merchant ON payment_orders(merchant_id);
CREATE INDEX idx_attempts_payment ON payment_attempts(payment_id);
CREATE INDEX idx_events_attempt ON processor_events(attempt_id);
CREATE INDEX idx_events_timestamp ON processor_events(event_timestamp);
CREATE INDEX idx_settlements_merchant_date
    ON settlement_batches(merchant_id, settlement_date);
CREATE INDEX idx_settlement_lines_batch ON settlement_lines(batch_id);
CREATE INDEX idx_bank_merchant_date
    ON bank_statement_lines(merchant_id, transaction_date);
CREATE INDEX idx_matches_status ON reconciliation_matches(status);
CREATE INDEX idx_exceptions_status ON exceptions(status);
CREATE INDEX idx_audit_entity ON audit_events(entity_type, entity_id);