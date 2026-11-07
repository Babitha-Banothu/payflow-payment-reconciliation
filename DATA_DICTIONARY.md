# Payment Reconciliation System — Data Dictionary

**Version:** 1.0  
**Random Seed:** 20261022  
**Currency representation:** Integer minor units (e.g. INR ₹100 = 10000 paise)  
**Timezone:** UTC for stored timestamps

## 1. Merchant

Purpose: Stores businesses accepting payments.

| Field | Type | Required | Validation |
|---|---|---|---|
| merchant_id | VARCHAR(30) | Yes | Unique, MER- prefixed |
| merchant_name | VARCHAR(150) | Yes | Non-empty |
| email | VARCHAR(255) | Yes | Unique, valid email |
| country | CHAR(2) | Yes | ISO country code |
| default_currency | CHAR(3) | Yes | ISO 4217 |
| status | VARCHAR(20) | Yes | ACTIVE, INACTIVE, SUSPENDED |
| created_at | TIMESTAMPTZ | Yes | Valid timestamp |

Primary key: merchant_id

## 2. PaymentOrder

Purpose: Represents a customer's payment request.

| Field | Type | Required | Validation |
|---|---|---|---|
| payment_id | VARCHAR(30) | Yes | PAY-2026-XXXXXXXX |
| merchant_id | VARCHAR(30) | Yes | FK to Merchant |
| customer_reference | VARCHAR(100) | No | Reference string |
| amount_minor | BIGINT | Yes | Greater than zero |
| currency | CHAR(3) | Yes | ISO 4217 |
| status | VARCHAR(20) | Yes | CREATED, PENDING, PAID, FAILED, REFUNDED, PARTIALLY_REFUNDED |
| created_at | TIMESTAMPTZ | Yes | Valid timestamp |
| updated_at | TIMESTAMPTZ | Yes | Must be >= created_at |

Primary key: payment_id  
Foreign key: merchant_id

## 3. PaymentAttempt

Purpose: Tracks individual attempts to process a payment.

| Field | Type | Required | Validation |
|---|---|---|---|
| attempt_id | VARCHAR(60) | Yes | ATT-<payment-id>-NN |
| payment_id | VARCHAR(30) | Yes | FK to PaymentOrder |
| attempt_number | SMALLINT | Yes | Greater than zero |
| processor_name | VARCHAR(50) | Yes | Non-empty |
| processor_reference | VARCHAR(100) | No | Unique when present |
| status | VARCHAR(20) | Yes | INITIATED, AUTHORIZED, CAPTURED, FAILED, CANCELLED |
| attempted_at | TIMESTAMPTZ | Yes | Valid timestamp |
| captured_at | TIMESTAMPTZ | No | >= attempted_at |

Primary key: attempt_id  
Foreign key: payment_id  
Unique constraint: payment_id + attempt_number

## 4. ProcessorEvent

Purpose: Records events received from payment processors.

| Field | Type | Required | Validation |
|---|---|---|---|
| event_id | VARCHAR(40) | Yes | Unique event identifier |
| attempt_id | VARCHAR(60) | Yes | FK to PaymentAttempt |
| processor_name | VARCHAR(50) | Yes | Non-empty |
| external_event_id | VARCHAR(100) | Yes | Unique per processor |
| event_type | VARCHAR(30) | Yes | INITIATED, AUTHORIZED, CAPTURED, FAILED, REFUNDED |
| event_status | VARCHAR(20) | Yes | RECEIVED, PROCESSED, REJECTED |
| event_timestamp | TIMESTAMPTZ | Yes | Processor event time |
| received_at | TIMESTAMPTZ | Yes | Ingestion time |
| payload_hash | VARCHAR(64) | Yes | SHA-256 hash |

Primary key: event_id  
Foreign key: attempt_id  
Unique constraint: processor_name + external_event_id

## 5. SettlementBatch

Purpose: Groups transactions for merchant settlement.

| Field | Type | Required | Validation |
|---|---|---|---|
| batch_id | VARCHAR(30) | Yes | SET-2026-XXXXXX |
| merchant_id | VARCHAR(30) | Yes | FK to Merchant |
| processor_name | VARCHAR(50) | Yes | Non-empty |
| currency | CHAR(3) | Yes | ISO 4217 |
| settlement_date | DATE | Yes | Valid date |
| status | VARCHAR(20) | Yes | GENERATED, SUBMITTED, SETTLED, DELAYED, FAILED |
| gross_amount_minor | BIGINT | Yes | Non-negative |
| refund_amount_minor | BIGINT | Yes | Non-negative |
| fee_amount_minor | BIGINT | Yes | Non-negative |
| net_amount_minor | BIGINT | Yes | Gross - refunds - fees |
| created_at | TIMESTAMPTZ | Yes | Valid timestamp |
| settled_at | TIMESTAMPTZ | No | >= created_at |

Primary key: batch_id  
Foreign key: merchant_id

## 6. SettlementLine

Purpose: Represents an individual financial transaction in a settlement batch.

| Field | Type | Required | Validation |
|---|---|---|---|
| settlement_line_id | VARCHAR(40) | Yes | STL-<batch-id>-NNN |
| batch_id | VARCHAR(30) | Yes | FK to SettlementBatch |
| attempt_id | VARCHAR(60) | Yes | FK to PaymentAttempt |
| line_type | VARCHAR(20) | Yes | CAPTURE, REFUND, FEE_ADJUSTMENT |
| currency | CHAR(3) | Yes | ISO 4217 |
| signed_amount_minor | BIGINT | Yes | Signed financial amount |
| fee_amount_minor | BIGINT | Yes | Non-negative |
| net_amount_minor | BIGINT | Derived | Signed amount - fee |
| created_at | TIMESTAMPTZ | Yes | Valid timestamp |

Primary key: settlement_line_id  
Foreign keys: batch_id, attempt_id

## 7. BankStatementLine

Purpose: Records actual bank credits and debits.

| Field | Type | Required | Validation |
|---|---|---|---|
| bank_line_id | VARCHAR(30) | Yes | BANK-2026-XXXXXX |
| merchant_id | VARCHAR(30) | Yes | FK to Merchant |
| bank_reference | VARCHAR(100) | No | Bank transaction reference |
| bank_account_reference | VARCHAR(100) | Yes | Synthetic account identifier |
| transaction_date | DATE | Yes | Valid date |
| value_date | DATE | No | >= transaction_date |
| currency | CHAR(3) | Yes | ISO 4217 |
| amount_minor | BIGINT | Yes | Signed amount |
| description | TEXT | No | Transaction description |
| created_at | TIMESTAMPTZ | Yes | Valid timestamp |

Primary key: bank_line_id  
Foreign key: merchant_id

## 8. ReconciliationMatch

Purpose: Records the decision made by the reconciliation engine.

| Field | Type | Required | Validation |
|---|---|---|---|
| match_id | VARCHAR(30) | Yes | REC-2026-XXXXXX |
| merchant_id | VARCHAR(30) | Yes | FK to Merchant |
| status | VARCHAR(20) | Yes | MATCHED, PARTIAL, UNMATCHED, REJECTED |
| matching_method | VARCHAR(30) | Yes | REFERENCE, AMOUNT_DATE, COMBINED |
| expected_amount_minor | BIGINT | Yes | Derived |
| actual_amount_minor | BIGINT | Yes | Derived |
| variance_minor | BIGINT | Yes | Actual - expected |
| currency | CHAR(3) | Yes | ISO 4217 |
| confidence_score | NUMERIC(5,4) | No | Between 0 and 1 |
| matched_at | TIMESTAMPTZ | Yes | Valid timestamp |

Primary key: match_id  
Foreign key: merchant_id

Supporting bridge: ReconciliationMatchItem.

## 9. Exception

Purpose: Stores reconciliation failures and anomalies.

| Field | Type | Required | Validation |
|---|---|---|---|
| exception_id | VARCHAR(30) | Yes | Unique identifier |
| merchant_id | VARCHAR(30) | Yes | FK to Merchant |
| match_id | VARCHAR(30) | No | FK to ReconciliationMatch |
| issue_type | VARCHAR(40) | Yes | Documented issue enum |
| severity | VARCHAR(20) | Yes | LOW, MEDIUM, HIGH, CRITICAL |
| status | VARCHAR(20) | Yes | OPEN, INVESTIGATING, RESOLVED, REJECTED |
| description | TEXT | Yes | Non-empty |
| detected_at | TIMESTAMPTZ | Yes | Valid timestamp |
| resolved_at | TIMESTAMPTZ | No | >= detected_at |

Primary key: exception_id  
Foreign keys: merchant_id, match_id

Supporting bridge: ExceptionItem.

## 10. Resolution

Purpose: Records investigation and resolution history.

| Field | Type | Required | Validation |
|---|---|---|---|
| resolution_id | VARCHAR(30) | Yes | Unique identifier |
| exception_id | VARCHAR(30) | Yes | FK to Exception |
| resolved_by | VARCHAR(100) | Yes | Analyst identifier |
| resolution_type | VARCHAR(40) | Yes | Documented resolution category |
| notes | TEXT | Yes | Non-empty |
| previous_status | VARCHAR(20) | Yes | Previous exception state |
| new_status | VARCHAR(20) | Yes | New exception state |
| created_at | TIMESTAMPTZ | Yes | Valid timestamp |

Primary key: resolution_id  
Foreign key: exception_id

## Supporting Tables

- ProcessorEventDelivery: Retains every webhook delivery, including duplicates.
- ReconciliationMatchItem: Links settlement and bank statement records.
- ExceptionItem: Links exceptions to their source records.
- AuditEvent: Preserves business state changes.

## Business Validation Rules

1. Every payment order must reference an existing merchant.
2. Every attempt must reference an existing payment order.
3. Every processor event must reference an existing attempt.
4. Captures cannot exceed the authorized payment amount.
5. Refunds cannot exceed captured amounts.
6. Settlement batch totals must equal their constituent financial lines.
7. Net settlement = captures - refunds - fees, with signed adjustment treatment documented.
8. Matching requires compatible merchant, currency, reference and configured date window.
9. Every unmatched record must create an exception.
10. Duplicate processor deliveries must not produce duplicate financial effects.
11. Resolution history must not overwrite previous exception history.
12. All monetary calculations must use integer minor units.

## Reproducibility

- Random seed: 20261022
- Dataset version: 1.0
- Synthetic data only
- Ground-truth labels stored separately
- All identifiers deterministic and immutable
