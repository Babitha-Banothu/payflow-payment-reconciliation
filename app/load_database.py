
import csv
import json
import os
from pathlib import Path

import psycopg


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "generated"
ENV_FILE = BASE_DIR / ".env"


def get_database_url():
    url = os.getenv("DATABASE_URL")

    if not url and ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()

            if line.startswith("DATABASE_URL="):
                url = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

    if not url:
        raise RuntimeError("DATABASE_URL not found")

    return url.replace(
        "postgresql+psycopg://",
        "postgresql://",
        1
    )


def read_csv(filename):
    path = DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Missing input file: {path}"
        )

    with path.open(
        "r",
        newline="",
        encoding="utf-8"
    ) as file:
        return list(csv.DictReader(file))


def nullable(value):
    return value if value not in ("", None) else None


def as_int(value):
    return int(value) if value not in ("", None) else None


def as_bool(value):
    return str(value).lower() == "true"


def execute_many(cur, sql, rows):
    if rows:
        cur.executemany(sql, rows)


# ============================================================
# LOAD CSV DATA
# ============================================================

def load_all():

    print("\nPAYMENT RECONCILIATION DATABASE LOADER")
    print("=" * 55)

    # Read all datasets before opening the transaction.

    merchants = read_csv("merchants.csv")
    orders = read_csv("payment_orders.csv")
    attempts = read_csv("payment_attempts.csv")

    events = (
        read_csv("processor_events.csv")
        + read_csv("processor_refund_events.csv")
    )

    deliveries = (
        read_csv("processor_event_deliveries.csv")
        + read_csv("processor_refund_deliveries.csv")
    )

    refunds = read_csv("refunds.csv")

    batches = read_csv("settlement_batches.csv")
    settlement_lines = read_csv("settlement_lines.csv")

    bank_lines = read_csv("bank_statement_lines.csv")
    expected = read_csv("expected_settlements.csv")

    matches = read_csv("reconciliation_matches.csv")
    exceptions = read_csv("exceptions.csv")
    exception_items = read_csv("exception_items.csv")

    summary = {
        "merchants": len(merchants),
        "payment_orders": len(orders),
        "payment_attempts": len(attempts),
        "processor_events": len(events),
        "processor_event_deliveries": len(deliveries),
        "refunds": len(refunds),
        "settlement_batches": len(batches),
        "settlement_lines": len(settlement_lines),
        "bank_statement_lines": len(bank_lines),
        "expected_settlements": len(expected),
        "reconciliation_matches": len(matches),
        "exceptions": len(exceptions),
        "exception_items": len(exception_items),
    }

    print("\nInput records:")

    for table, count in summary.items():
        print(f"{table:32s}: {count:,}")

    # Build lookups for relationship validation.

    merchant_ids = {
        row["merchant_id"] for row in merchants
    }

    payment_lookup = {
        row["payment_id"]: row for row in orders
    }

    attempt_lookup = {
        row["attempt_id"]: row for row in attempts
    }

    batch_lookup = {
        row["batch_id"]: row for row in batches
    }

    bank_lookup = {
        row["bank_line_id"]: row for row in bank_lines
    }

    event_ids = {
        row["event_id"] for row in events
    }

    settlement_line_lookup = {
        row["settlement_line_id"]: row
        for row in settlement_lines
    }

    match_lookup = {
        row["match_id"]: row
        for row in matches
    }

    # Validate source relationships before writing.

    assert len(merchant_ids) == len(merchants)
    assert len(payment_lookup) == len(orders)
    assert len(attempt_lookup) == len(attempts)
    assert len(batch_lookup) == len(batches)
    assert len(bank_lookup) == len(bank_lines)
    assert len(event_ids) == len(events)
    assert len(settlement_line_lookup) == len(settlement_lines)

    for row in orders:
        assert row["merchant_id"] in merchant_ids

    for row in attempts:
        assert row["payment_id"] in payment_lookup

    for row in events:
        assert row["attempt_id"] in attempt_lookup

    for row in deliveries:
        assert row["event_id"] in event_ids

    for row in refunds:
        assert row["payment_id"] in payment_lookup
        assert row["attempt_id"] in attempt_lookup
        assert row["merchant_id"] in merchant_ids

    for row in settlement_lines:
        assert row["batch_id"] in batch_lookup
        assert row["attempt_id"] in attempt_lookup

    for row in bank_lines:
        assert row["merchant_id"] in merchant_ids
        assert row["batch_reference"] in batch_lookup

    for row in expected:
        assert row["batch_id"] in batch_lookup

    for row in matches:
        assert row["batch_id"] in batch_lookup

        if row["bank_line_id"]:
            assert row["bank_line_id"] in bank_lookup

    for row in exceptions:
        if row["batch_id"]:
            assert row["batch_id"] in batch_lookup

        if row["bank_line_id"]:
            assert row["bank_line_id"] in bank_lookup

    for row in exception_items:
        assert row["exception_id"] in {
            item["exception_id"] for item in exceptions
        }

        if row["settlement_line_id"]:
            assert (
                row["settlement_line_id"]
                in settlement_line_lookup
            )

        if row["bank_line_id"]:
            assert row["bank_line_id"] in bank_lookup

    print("\nSource relationships: VALID")

    # Map match rows by batch and bank line.

    match_by_batch_bank = {}

    first_match_by_batch = {}

    for row in matches:
        key = (
            row["batch_id"],
            nullable(row["bank_line_id"])
        )

        match_by_batch_bank[key] = row["match_id"]

        first_match_by_batch.setdefault(
            row["batch_id"],
            row["match_id"]
        )

    # Prepare settlement lines by batch.

    lines_by_batch = {}

    for row in settlement_lines:
        lines_by_batch.setdefault(
            row["batch_id"], []
        ).append(row)

    database_url = get_database_url()

    # All destructive and insertion work is inside
    # one transaction. Failure rolls everything back.

    print("\nConnecting to PostgreSQL...")

    with psycopg.connect(database_url) as conn:

        with conn.transaction():

            with conn.cursor() as cur:

                # --------------------------------------
                # CLEAR PREVIOUS SYNTHETIC DATA
                # --------------------------------------

                print("Preparing database for dataset reload...")

                cur.execute("""
                    TRUNCATE TABLE
                        audit_events,
                        resolutions,
                        exception_items,
                        exceptions,
                        reconciliation_match_items,
                        reconciliation_matches,
                        synthetic_ground_truth,
                        expected_settlements,
                        refunds,
                        bank_statement_lines,
                        settlement_lines,
                        settlement_batches,
                        processor_event_deliveries,
                        processor_events,
                        payment_attempts,
                        payment_orders,
                        merchants
                    RESTART IDENTITY CASCADE
                """)

                # --------------------------------------
                # 1. MERCHANTS
                # --------------------------------------

                execute_many(
                    cur,
                    """
                    INSERT INTO merchants (
                        merchant_id,
                        merchant_name,
                        email,
                        country,
                        default_currency,
                        status,
                        created_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                    """,
                    [
                        (
                            r["merchant_id"],
                            r["merchant_name"],
                            r["email"],
                            r["country"],
                            r["default_currency"],
                            r["status"],
                            r["created_at"]
                        )
                        for r in merchants
                    ]
                )

                # --------------------------------------
                # 2. PAYMENT ORDERS
                # --------------------------------------

                execute_many(
                    cur,
                    """
                    INSERT INTO payment_orders (
                        payment_id,
                        merchant_id,
                        customer_reference,
                        amount_minor,
                        currency,
                        status,
                        created_at,
                        updated_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    [
                        (
                            r["payment_id"],
                            r["merchant_id"],
                            nullable(r["customer_reference"]),
                            int(r["amount_minor"]),
                            r["currency"],
                            r["status"],
                            r["created_at"],
                            r["updated_at"]
                        )
                        for r in orders
                    ]
                )

                # --------------------------------------
                # 3. PAYMENT ATTEMPTS
                # --------------------------------------

                execute_many(
                    cur,
                    """
                    INSERT INTO payment_attempts (
                        attempt_id,
                        payment_id,
                        attempt_number,
                        processor_name,
                        processor_reference,
                        status,
                        attempted_at,
                        captured_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    [
                        (
                            r["attempt_id"],
                            r["payment_id"],
                            int(r["attempt_number"]),
                            r["processor_name"],
                            nullable(r["processor_reference"]),
                            r["status"],
                            r["attempted_at"],
                            nullable(r["captured_at"])
                        )
                        for r in attempts
                    ]
                )

                # --------------------------------------
                # 4. PROCESSOR EVENTS
                # --------------------------------------

                execute_many(
                    cur,
                    """
                    INSERT INTO processor_events (
                        event_id,
                        attempt_id,
                        processor_name,
                        external_event_id,
                        event_type,
                        event_status,
                        event_timestamp,
                        received_at,
                        payload_hash
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    [
                        (
                            r["event_id"],
                            r["attempt_id"],
                            r["processor_name"],
                            r["external_event_id"],
                            r["event_type"],
                            r["event_status"],
                            r["event_timestamp"],
                            r["received_at"],
                            r["payload_hash"]
                        )
                        for r in events
                    ]
                )

                # --------------------------------------
                # 5. PROCESSOR EVENT DELIVERIES
                # --------------------------------------

                execute_many(
                    cur,
                    """
                    INSERT INTO processor_event_deliveries (
                        delivery_id,
                        event_id,
                        received_at,
                        payload_hash,
                        is_duplicate
                    )
                    VALUES (%s,%s,%s,%s,%s)
                    """,
                    [
                        (
                            r["delivery_id"],
                            r["event_id"],
                            r["received_at"],
                            r["payload_hash"],
                            as_bool(r["is_duplicate"])
                        )
                        for r in deliveries
                    ]
                )

                # --------------------------------------
                # 6. REFUNDS
                # --------------------------------------

                execute_many(
                    cur,
                    """
                    INSERT INTO refunds (
                        refund_id,
                        payment_id,
                        attempt_id,
                        merchant_id,
                        amount_minor,
                        currency,
                        status,
                        refund_timestamp
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    [
                        (
                            r["refund_id"],
                            r["payment_id"],
                            r["attempt_id"],
                            r["merchant_id"],
                            int(r["amount_minor"]),
                            r["currency"],
                            r["status"],
                            r["refund_timestamp"]
                        )
                        for r in refunds
                    ]
                )

                # --------------------------------------
                # 7. SETTLEMENT BATCHES
                # --------------------------------------

                execute_many(
                    cur,
                    """
                    INSERT INTO settlement_batches (
                        batch_id,
                        merchant_id,
                        processor_name,
                        currency,
                        settlement_date,
                        status,
                        gross_amount_minor,
                        refund_amount_minor,
                        fee_amount_minor,
                        net_amount_minor,
                        created_at,
                        settled_at
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                    )
                    """,
                    [
                        (
                            r["batch_id"],
                            r["merchant_id"],
                            r["processor_name"],
                            r["currency"],
                            r["settlement_date"],
                            r["status"],
                            int(r["gross_amount_minor"]),
                            int(r["refund_amount_minor"]),
                            int(r["fee_amount_minor"]),
                            int(r["net_amount_minor"]),
                            r["created_at"],
                            nullable(r["settled_at"])
                        )
                        for r in batches
                    ]
                )

                # --------------------------------------
                # 8. SETTLEMENT LINES
                # --------------------------------------

                # net_amount_minor is GENERATED ALWAYS in SQL.
                # Insert the source fields only.

                execute_many(
                    cur,
                    """
                    INSERT INTO settlement_lines (
                        settlement_line_id,
                        batch_id,
                        attempt_id,
                        line_type,
                        currency,
                        signed_amount_minor,
                        fee_amount_minor,
                        created_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    [
                        (
                            r["settlement_line_id"],
                            r["batch_id"],
                            r["attempt_id"],
                            r["line_type"],
                            r["currency"],
                            int(r["signed_amount_minor"]),
                            int(r["fee_amount_minor"]),
                            r["created_at"]
                        )
                        for r in settlement_lines
                    ]
                )

                # Verify generated database amounts.

                cur.execute("""
                    SELECT COUNT(*)
                    FROM settlement_lines
                    WHERE net_amount_minor <>
                        signed_amount_minor - fee_amount_minor
                """)

                assert cur.fetchone()[0] == 0

                # --------------------------------------
                # 9. BANK STATEMENT LINES
                # --------------------------------------

                execute_many(
                    cur,
                    """
                    INSERT INTO bank_statement_lines (
                        bank_line_id,
                        merchant_id,
                        bank_reference,
                        bank_account_reference,
                        transaction_date,
                        value_date,
                        currency,
                        amount_minor,
                        description,
                        created_at,
                        batch_id,
                        bank_name,
                        transaction_type,
                        transaction_timestamp
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s
                    )
                    """,
                    [
                        (
                            r["bank_line_id"],
                            r["merchant_id"],
                            r["batch_reference"],
                            f"SYNTHETIC-ACCOUNT-{r['merchant_id']}",
                            r["transaction_timestamp"][:10],
                            r["transaction_timestamp"][:10],
                            r["currency"],
                            int(r["amount_minor"]),
                            r["description"],
                            r["transaction_timestamp"],
                            r["batch_reference"],
                            r["bank_name"],
                            r["transaction_type"],
                            r["transaction_timestamp"]
                        )
                        for r in bank_lines
                    ]
                )

                # --------------------------------------
                # 10. EXPECTED SETTLEMENTS
                # --------------------------------------

                execute_many(
                    cur,
                    """
                    INSERT INTO expected_settlements (
                        expected_settlement_id,
                        batch_id,
                        merchant_id,
                        processor_name,
                        currency,
                        expected_amount_minor,
                        expected_date,
                        status
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    [
                        (
                            r["expected_settlement_id"],
                            r["batch_id"],
                            r["merchant_id"],
                            r["processor_name"],
                            r["currency"],
                            int(r["expected_amount_minor"]),
                            r["expected_date"],
                            r["status"]
                        )
                        for r in expected
                    ]
                )

                # --------------------------------------
                # 11. RECONCILIATION MATCHES
                # --------------------------------------

                execute_many(
                    cur,
                    """
                    INSERT INTO reconciliation_matches (
                        match_id,
                        merchant_id,
                        status,
                        matching_method,
                        expected_amount_minor,
                        actual_amount_minor,
                        variance_minor,
                        currency,
                        confidence_score,
                        matched_at,
                        batch_id,
                        bank_line_id,
                        expected_currency,
                        actual_currency
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s
                    )
                    """,
                    [
                        (
                            r["match_id"],
                            batch_lookup[r["batch_id"]]["merchant_id"],
                            r["status"],
                            r["matching_method"],
                            int(r["expected_amount_minor"]),
                            as_int(r["actual_amount_minor"]) or 0,
                            as_int(r["amount_difference_minor"]) or 0,
                            r["expected_currency"],
                            float(r["confidence_score"]),
                            r["created_at"],
                            r["batch_id"],
                            nullable(r["bank_line_id"]),
                            r["expected_currency"],
                            nullable(r["actual_currency"])
                        )
                        for r in matches
                    ]
                )

                # --------------------------------------
                # 12. RECONCILIATION MATCH ITEMS
                # --------------------------------------

                match_items = []

                for match in matches:

                    batch_id = match["batch_id"]

                    bank_line_id = nullable(
                        match["bank_line_id"]
                    )

                    source_lines = lines_by_batch.get(
                        batch_id, []
                    )

                    if source_lines:

                        for index, line in enumerate(source_lines):

                            # Associate the bank line with the
                            # first settlement line. Other lines
                            # retain their own source reference.

                            match_items.append((
                                match["match_id"],
                                line["settlement_line_id"],
                                bank_line_id if index == 0 else None,
                                int(line["net_amount_minor"])
                            ))

                    elif bank_line_id:

                        match_items.append((
                            match["match_id"],
                            None,
                            bank_line_id,
                            int(bank_lookup[bank_line_id]["amount_minor"])
                        ))

                execute_many(
                    cur,
                    """
                    INSERT INTO reconciliation_match_items (
                        match_id,
                        settlement_line_id,
                        bank_line_id,
                        allocated_amount_minor
                    )
                    VALUES (%s,%s,%s,%s)
                    """,
                    match_items
                )

                # --------------------------------------
                # 13. EXCEPTIONS
                # --------------------------------------

                exception_rows = []

                for r in exceptions:

                    batch_id = nullable(r["batch_id"])

                    bank_line_id = nullable(
                        r["bank_line_id"]
                    )

                    match_id = match_by_batch_bank.get(
                        (batch_id, bank_line_id)
                    )

                    if not match_id and batch_id:
                        match_id = first_match_by_batch.get(
                            batch_id
                        )

                    if batch_id:
                        merchant_id = (
                            batch_lookup[batch_id]["merchant_id"]
                        )
                    elif bank_line_id:
                        merchant_id = (
                            bank_lookup[bank_line_id]["merchant_id"]
                        )
                    else:
                        raise ValueError(
                            f"Cannot identify merchant for {r['exception_id']}"
                        )

                    exception_rows.append((
                        r["exception_id"],
                        merchant_id,
                        match_id,
                        r["issue_type"],
                        r["severity"],
                        r["status"],
                        r["description"],
                        r["detected_at"],
                        batch_id,
                        bank_line_id
                    ))

                execute_many(
                    cur,
                    """
                    INSERT INTO exceptions (
                        exception_id,
                        merchant_id,
                        match_id,
                        issue_type,
                        severity,
                        status,
                        description,
                        detected_at,
                        batch_id,
                        bank_line_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                    )
                    """,
                    exception_rows
                )

                # --------------------------------------
                # 14. EXCEPTION ITEMS
                # --------------------------------------

                execute_many(
                    cur,
                    """
                    INSERT INTO exception_items (
                        exception_id,
                        settlement_line_id,
                        bank_line_id,
                        external_exception_item_id,
                        source_type
                    )
                    VALUES (%s,%s,%s,%s,%s)
                    """,
                    [
                        (
                            r["exception_id"],
                            nullable(r["settlement_line_id"]),
                            nullable(r["bank_line_id"]),
                            r["exception_item_id"],
                            r["source_type"]
                        )
                        for r in exception_items
                    ]
                )

                # --------------------------------------
                # 15. SYNTHETIC GROUND TRUTH
                # --------------------------------------

                ground_truth = []

                for r in bank_lines:

                    if r["anomaly_type"] != "NONE":

                        ground_truth.append((
                            "BANK_STATEMENT_LINE",
                            r["bank_line_id"],
                            r["anomaly_type"],
                            json.dumps({
                                "batch_id": r["batch_reference"]
                            })
                        ))

                for r in expected:

                    ground_truth.append((
                        "EXPECTED_SETTLEMENT",
                        r["expected_settlement_id"],
                        r["status"],
                        json.dumps({
                            "batch_id": r["batch_id"]
                        })
                    ))

                execute_many(
                    cur,
                    """
                    INSERT INTO synthetic_ground_truth (
                        entity_type,
                        entity_id,
                        label,
                        metadata
                    )
                    VALUES (
                        %s,%s,%s,%s::jsonb
                    )
                    """,
                    ground_truth
                )

                # --------------------------------------
                # 16. DATABASE VALIDATION
                # --------------------------------------

                expected_counts = {
                    "merchants": len(merchants),
                    "payment_orders": len(orders),
                    "payment_attempts": len(attempts),
                    "processor_events": len(events),
                    "processor_event_deliveries": len(deliveries),
                    "refunds": len(refunds),
                    "settlement_batches": len(batches),
                    "settlement_lines": len(settlement_lines),
                    "bank_statement_lines": len(bank_lines),
                    "expected_settlements": len(expected),
                    "reconciliation_matches": len(matches),
                    "exceptions": len(exceptions),
                    "exception_items": len(exception_items),
                }

                print("\nDatabase row counts:")

                for table, expected_count in expected_counts.items():

                    cur.execute(
                        f"SELECT COUNT(*) FROM {table}"
                    )

                    actual_count = cur.fetchone()[0]

                    print(
                        f"{table:32s}: {actual_count:,}"
                    )

                    assert actual_count == expected_count, (
                        f"Row count mismatch in {table}: "
                        f"expected {expected_count}, got {actual_count}"
                    )

                # Financial consistency.

                cur.execute("""
                    SELECT COUNT(*)
                    FROM settlement_batches
                    WHERE net_amount_minor <>
                        gross_amount_minor
                        - refund_amount_minor
                        - fee_amount_minor
                """)

                assert cur.fetchone()[0] == 0

                # Foreign-key validation.

                cur.execute("""
                    SELECT COUNT(*)
                    FROM settlement_lines sl
                    LEFT JOIN settlement_batches sb
                        ON sl.batch_id = sb.batch_id
                    LEFT JOIN payment_attempts pa
                        ON sl.attempt_id = pa.attempt_id
                    WHERE sb.batch_id IS NULL
                       OR pa.attempt_id IS NULL
                """)

                assert cur.fetchone()[0] == 0

                print("\nAll database validations passed.")

        # The transaction commits here.

    print("\n" + "=" * 55)
    print("DATABASE IMPORT COMPLETED")
    print("=" * 55)
    print("Transaction       : COMMITTED")
    print("Foreign keys      : VALID")
    print("Financial checks  : VALID")
    print("Row counts        : VALID")
    print("Ground truth      : STORED SEPARATELY")
    print("=" * 55)


if __name__ == "__main__":
    load_all()
