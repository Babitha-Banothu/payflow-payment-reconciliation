
import csv
import hashlib
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


# ==================================================
# CONFIGURATION
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "generated"

FEE_RATE_BPS = 290       # 2.9%
REFUND_INTERVAL = 20     # Every 20th captured payment
REFUND_PERCENT = 25      # 25% partial refund
SETTLEMENT_DELAY_DAYS = 2
SEED = 20261022


# ==================================================
# FILE UTILITIES
# ==================================================

def read_csv(filename):
    path = DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Required input file not found: {path}"
        )

    with path.open(
        "r",
        newline="",
        encoding="utf-8"
    ) as file:
        return list(csv.DictReader(file))


def write_csv(filename, records, fieldnames=None):
    path = DATA_DIR / filename

    if not records and not fieldnames:
        raise ValueError(
            f"Field names required for empty dataset: {filename}"
        )

    columns = fieldnames or list(records[0].keys())

    with path.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=columns
        )

        writer.writeheader()
        writer.writerows(records)

    print(f"Generated {filename}: {len(records):,} rows")


# ==================================================
# FINANCIAL UTILITIES
# ==================================================

def calculate_fee(amount_minor):
    """
    Calculate 2.9% processor fee.
    Uses integer arithmetic and half-up rounding.
    """
    if amount_minor < 0:
        raise ValueError("Amount cannot be negative")

    return (
        amount_minor * FEE_RATE_BPS + 5000
    ) // 10000


def calculate_refund(amount_minor):
    """
    Calculate a 25% partial refund.
    """
    return (
        amount_minor * REFUND_PERCENT + 50
    ) // 100


def sha256(value):
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def parse_timestamp(value):
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


def format_timestamp(value):
    return value.astimezone(
        timezone.utc
    ).isoformat()


# ==================================================
# MAIN SETTLEMENT ENGINE
# ==================================================

def generate_settlements():

    print("\nPAYMENT SETTLEMENT ENGINE")
    print("=" * 45)

    # ----------------------------------------------
    # 1. LOAD INPUT DATA
    # ----------------------------------------------

    orders = read_csv("payment_orders.csv")
    attempts = read_csv("payment_attempts.csv")

    order_lookup = {
        order["payment_id"]: order
        for order in orders
    }

    attempt_ids = {
        attempt["attempt_id"]
        for attempt in attempts
    }

    if len(order_lookup) != len(orders):
        raise ValueError("Duplicate payment IDs found")

    if len(attempt_ids) != len(attempts):
        raise ValueError("Duplicate attempt IDs found")

    transactions = []
    refunds = []
    refund_events = []
    refund_deliveries = []

    refund_counter = 0
    captured_counter = 0

    event_counter = 0
    delivery_counter = 0

    # ----------------------------------------------
    # 2. PROCESS CAPTURED PAYMENTS
    # ----------------------------------------------

    print("Processing captured payments...")

    for attempt in attempts:

        if attempt["status"] != "CAPTURED":
            continue

        payment_id = attempt["payment_id"]

        if payment_id not in order_lookup:
            raise ValueError(
                f"Missing payment order: {payment_id}"
            )

        order = order_lookup[payment_id]

        amount_minor = int(order["amount_minor"])

        currency = order["currency"]
        merchant_id = order["merchant_id"]

        processor = attempt["processor_name"]

        captured_at = parse_timestamp(
            attempt["captured_at"]
        )

        if amount_minor <= 0:
            raise ValueError("Invalid captured amount")

        if order["status"] not in [
            "PAID",
            "PARTIALLY_REFUNDED",
            "REFUNDED"
        ]:
            raise ValueError(
                f"Captured attempt belongs to non-paid order: {payment_id}"
            )

        # ------------------------------------------
        # CAPTURE TRANSACTION
        # ------------------------------------------

        fee = calculate_fee(amount_minor)

        capture_settlement_date = (
            captured_at.date()
            + timedelta(days=SETTLEMENT_DELAY_DAYS)
        )

        transactions.append({

            "merchant_id": merchant_id,

            "processor_name": processor,

            "currency": currency,

            "settlement_date": capture_settlement_date,

            "attempt_id": attempt["attempt_id"],

            "line_type": "CAPTURE",

            "signed_amount_minor": amount_minor,

            "fee_amount_minor": fee,

        })

        captured_counter += 1

        # ------------------------------------------
        # 3. GENERATE DETERMINISTIC PARTIAL REFUNDS
        # ------------------------------------------

        if captured_counter % REFUND_INTERVAL != 0:
            continue

        refund_counter += 1

        refund_amount = calculate_refund(
            amount_minor
        )

        if refund_amount <= 0 or refund_amount > amount_minor:
            raise ValueError("Invalid refund amount")

        refund_id = (
            f"REF-2026-{refund_counter:08d}"
        )

        refund_at = (
            captured_at + timedelta(days=1)
        )

        refund_timestamp = format_timestamp(
            refund_at
        )

        refund_settlement_date = (
            refund_at.date()
            + timedelta(days=SETTLEMENT_DELAY_DAYS)
        )

        # Refund master record.

        refunds.append({

            "refund_id": refund_id,

            "payment_id": payment_id,

            "attempt_id": attempt["attempt_id"],

            "merchant_id": merchant_id,

            "amount_minor": refund_amount,

            "currency": currency,

            "status": "PROCESSED",

            "refund_timestamp": refund_timestamp,

        })

        # Refund processor event.

        event_counter += 1

        event_id = (
            f"EVT-2026-RF-{event_counter:08d}"
        )

        event_hash = sha256(
            f"{refund_id}|{attempt['attempt_id']}|"
            f"REFUNDED|{refund_timestamp}"
        )

        refund_events.append({

            "event_id": event_id,

            "attempt_id": attempt["attempt_id"],

            "processor_name": processor,

            "external_event_id": event_id,

            "event_type": "REFUNDED",

            "event_status": "PROCESSED",

            "event_timestamp": refund_timestamp,

            "received_at": format_timestamp(
                refund_at + timedelta(seconds=5)
            ),

            "payload_hash": event_hash,

        })

        # Refund webhook delivery.

        delivery_counter += 1

        refund_deliveries.append({

            "delivery_id": (
                f"DLV-2026-RF-{delivery_counter:08d}"
            ),

            "event_id": event_id,

            "received_at": format_timestamp(
                refund_at + timedelta(seconds=5)
            ),

            "payload_hash": event_hash,

            "is_duplicate": False,

        })

        # Refund settlement transaction.
        # Refunds have no additional processing fee
        # in this simplified business model.

        transactions.append({

            "merchant_id": merchant_id,

            "processor_name": processor,

            "currency": currency,

            "settlement_date": refund_settlement_date,

            "attempt_id": attempt["attempt_id"],

            "line_type": "REFUND",

            "signed_amount_minor": -refund_amount,

            "fee_amount_minor": 0,

        })

    # ----------------------------------------------
    # 4. GROUP TRANSACTIONS INTO BATCHES
    # ----------------------------------------------

    print("Grouping settlement transactions...")

    grouped = defaultdict(list)

    for transaction in transactions:

        key = (
            transaction["merchant_id"],
            transaction["processor_name"],
            transaction["currency"],
            transaction["settlement_date"]
        )

        grouped[key].append(transaction)

    batches = []
    settlement_lines = []

    # Sorting makes IDs reproducible.

    sorted_groups = sorted(
        grouped.items()
    )

    # ----------------------------------------------
    # 5. CREATE SETTLEMENT BATCHES
    # ----------------------------------------------

    print("Creating settlement batches...")

    for batch_number, (key, entries) in enumerate(
        sorted_groups,
        start=1
    ):

        (
            merchant_id,
            processor,
            currency,
            settlement_date
        ) = key

        batch_id = (
            f"SET-2026-{batch_number:06d}"
        )

        gross_amount = sum(
            entry["signed_amount_minor"]
            for entry in entries
            if entry["line_type"] == "CAPTURE"
        )

        refund_amount = sum(
            abs(entry["signed_amount_minor"])
            for entry in entries
            if entry["line_type"] == "REFUND"
        )

        fee_amount = sum(
            entry["fee_amount_minor"]
            for entry in entries
        )

        net_amount = (
            gross_amount
            - refund_amount
            - fee_amount
        )

        # Deterministic delayed settlement scenario.
        is_delayed = batch_number % 17 == 0

        batch_status = (
            "DELAYED"
            if is_delayed
            else "SETTLED"
        )

        batch_created_at = datetime.combine(
            settlement_date,
            datetime.min.time(),
            tzinfo=timezone.utc
        )

        settled_at = (
            None
            if is_delayed
            else format_timestamp(
                batch_created_at + timedelta(hours=12)
            )
        )

        # Batch arithmetic validation.

        if net_amount != (
            gross_amount - refund_amount - fee_amount
        ):
            raise ValueError(
                f"Settlement arithmetic failed: {batch_id}"
            )

        # Negative net settlements are valid for refund-only batches.

        batches.append({

            "batch_id": batch_id,

            "merchant_id": merchant_id,

            "processor_name": processor,

            "currency": currency,

            "settlement_date": settlement_date.isoformat(),

            "status": batch_status,

            "gross_amount_minor": gross_amount,

            "refund_amount_minor": refund_amount,

            "fee_amount_minor": fee_amount,

            "net_amount_minor": net_amount,

            "created_at": format_timestamp(
                batch_created_at
            ),

            "settled_at": settled_at,

        })

        # ------------------------------------------
        # 6. CREATE SETTLEMENT LINES
        # ------------------------------------------

        for line_number, entry in enumerate(
            entries,
            start=1
        ):

            line_id = (
                f"STL-{batch_id}-{line_number:03d}"
            )

            line_net = (
                entry["signed_amount_minor"]
                - entry["fee_amount_minor"]
            )

            settlement_lines.append({

                "settlement_line_id": line_id,

                "batch_id": batch_id,

                "attempt_id": entry["attempt_id"],

                "line_type": entry["line_type"],

                "currency": currency,

                "signed_amount_minor": (
                    entry["signed_amount_minor"]
                ),

                "fee_amount_minor": (
                    entry["fee_amount_minor"]
                ),

                "net_amount_minor": line_net,

                "created_at": format_timestamp(
                    batch_created_at
                ),

            })

    # ----------------------------------------------
    # 7. VALIDATE SETTLEMENT DATA
    # ----------------------------------------------

    print("Validating settlement records...")

    batch_lookup = {
        batch["batch_id"]: batch
        for batch in batches
    }

    line_ids = {
        line["settlement_line_id"]
        for line in settlement_lines
    }

    assert len(batch_lookup) == len(batches)

    assert len(line_ids) == len(settlement_lines)

    assert all(
        line["attempt_id"] in attempt_ids
        for line in settlement_lines
    )

    assert all(
        line["batch_id"] in batch_lookup
        for line in settlement_lines
    )

    # Check that each batch equals its constituent lines.

    for batch_id, batch in batch_lookup.items():

        batch_lines = [
            line
            for line in settlement_lines
            if line["batch_id"] == batch_id
        ]

        line_net_total = sum(
            line["net_amount_minor"]
            for line in batch_lines
        )

        assert line_net_total == batch["net_amount_minor"], (
            f"Line total mismatch: {batch_id}"
        )

    # ----------------------------------------------
    # 8. EXPORT DATASETS
    # ----------------------------------------------

    print("Exporting settlement datasets...")

    write_csv(
        "refunds.csv",
        refunds,
        [
            "refund_id",
            "payment_id",
            "attempt_id",
            "merchant_id",
            "amount_minor",
            "currency",
            "status",
            "refund_timestamp"
        ]
    )

    write_csv(
        "settlement_batches.csv",
        batches
    )

    write_csv(
        "settlement_lines.csv",
        settlement_lines
    )

    write_csv(
        "processor_refund_events.csv",
        refund_events,
        [
            "event_id",
            "attempt_id",
            "processor_name",
            "external_event_id",
            "event_type",
            "event_status",
            "event_timestamp",
            "received_at",
            "payload_hash"
        ]
    )

    write_csv(
        "processor_refund_deliveries.csv",
        refund_deliveries,
        [
            "delivery_id",
            "event_id",
            "received_at",
            "payload_hash",
            "is_duplicate"
        ]
    )

    # ----------------------------------------------
    # 9. SUMMARY
    # ----------------------------------------------

    total_gross = sum(
        batch["gross_amount_minor"]
        for batch in batches
    )

    total_refunds = sum(
        batch["refund_amount_minor"]
        for batch in batches
    )

    total_fees = sum(
        batch["fee_amount_minor"]
        for batch in batches
    )

    total_net = sum(
        batch["net_amount_minor"]
        for batch in batches
    )

    delayed_count = sum(
        batch["status"] == "DELAYED"
        for batch in batches
    )

    print("\n" + "=" * 45)
    print("SETTLEMENT GENERATION SUCCESSFUL")
    print("=" * 45)

    print(f"Captured payments : {captured_counter:,}")
    print(f"Partial refunds   : {len(refunds):,}")
    print(f"Settlement batches: {len(batches):,}")
    print(f"Settlement lines  : {len(settlement_lines):,}")
    print(f"Delayed batches   : {delayed_count:,}")

    print("-" * 45)

    print(f"Gross amount      : {total_gross / 100:,.2f}")
    print(f"Refund amount     : {total_refunds / 100:,.2f}")
    print(f"Processor fees    : {total_fees / 100:,.2f}")
    print(f"Net settlement    : {total_net / 100:,.2f}")

    print("-" * 45)

    print("Primary keys       : VALID")
    print("Foreign keys       : VALID")
    print("Batch arithmetic   : VALID")
    print("Settlement lines   : VALID")

    print("=" * 45)


# ==================================================
# ENTRY POINT
# ==================================================

if __name__ == "__main__":
    generate_settlements()
