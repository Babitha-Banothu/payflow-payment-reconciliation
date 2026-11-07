
import csv
import hashlib
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


# ==================================================
# CONFIGURATION
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "generated"

SEED = 20261022

# Deterministic anomaly rates.
MISSING_DEPOSIT_RATE = 0.02
DUPLICATE_DEPOSIT_RATE = 0.02
AMOUNT_MISMATCH_RATE = 0.02
CURRENCY_MISMATCH_RATE = 0.01

BANK_NAME = "SYNTHETIC_BANK"


# ==================================================
# FILE UTILITIES
# ==================================================

def read_csv(filename):
    path = DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Required file not found: {path}"
        )

    with path.open(
        "r",
        newline="",
        encoding="utf-8"
    ) as file:
        return list(csv.DictReader(file))


def write_csv(filename, records, fieldnames):
    path = DATA_DIR / filename

    with path.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )
        writer.writeheader()
        writer.writerows(records)

    print(f"Generated {filename}: {len(records):,} rows")


def stable_number(value):
    """
    Produce a reproducible integer from a string.
    """
    digest = hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()

    return int(digest[:12], 16)


def format_timestamp(value):
    return value.astimezone(
        timezone.utc
    ).isoformat()


# ==================================================
# BANK STATEMENT GENERATOR
# ==================================================

def generate_bank_statements():

    print("\nBANK STATEMENT GENERATOR")
    print("=" * 45)

    batches = read_csv("settlement_batches.csv")

    if not batches:
        raise ValueError("No settlement batches found")

    bank_lines = []
    expected_settlements = []

    bank_counter = 0

    anomaly_counts = Counter()

    seen_batch_ids = set()

    # ----------------------------------------------
    # 1. VALIDATE INPUT BATCHES
    # ----------------------------------------------

    for batch in batches:

        batch_id = batch["batch_id"]

        if batch_id in seen_batch_ids:
            raise ValueError(
                f"Duplicate settlement batch: {batch_id}"
            )

        seen_batch_ids.add(batch_id)

        if int(batch["net_amount_minor"]) == 0:
            raise ValueError(
                f"Zero-value settlement batch: {batch_id}"
            )

        if batch["status"] not in ["SETTLED", "DELAYED"]:
            raise ValueError(
                f"Unexpected batch status: {batch['status']}"
            )

    # ----------------------------------------------
    # 2. PROCESS SETTLEMENT BATCHES
    # ----------------------------------------------

    print("Generating bank statement entries...")

    for batch in batches:

        batch_id = batch["batch_id"]

        status = batch["status"]

        amount = int(batch["net_amount_minor"])

        currency = batch["currency"]

        settlement_date = datetime.fromisoformat(
            batch["settlement_date"]
        ).date()

        # Expected bank arrival date.
        expected_date = (
            settlement_date + timedelta(days=1)
        )

        # ------------------------------------------
        # DELAYED SETTLEMENTS
        # ------------------------------------------

        if status == "DELAYED":

            expected_settlements.append({

                "expected_settlement_id": (
                    f"EXP-{batch_id}"
                ),

                "batch_id": batch_id,

                "merchant_id": batch["merchant_id"],

                "processor_name": batch["processor_name"],

                "currency": currency,

                "expected_amount_minor": amount,

                "expected_date": expected_date.isoformat(),

                "status": "DELAYED",

            })

            anomaly_counts["DELAYED_SETTLEMENT"] += 1

            # Do not invent a bank transaction for a
            # settlement that has not arrived.

            continue

        # ------------------------------------------
        # DETERMINISTIC ANOMALY SELECTION
        # ------------------------------------------

        score = stable_number(
            f"{SEED}|{batch_id}"
        ) % 10000

        missing_limit = int(
            MISSING_DEPOSIT_RATE * 10000
        )

        duplicate_limit = (
            missing_limit
            + int(DUPLICATE_DEPOSIT_RATE * 10000)
        )

        amount_limit = (
            duplicate_limit
            + int(AMOUNT_MISMATCH_RATE * 10000)
        )

        currency_limit = (
            amount_limit
            + int(CURRENCY_MISMATCH_RATE * 10000)
        )

        # ------------------------------------------
        # MISSING DEPOSIT
        # ------------------------------------------

        if score < missing_limit:

            expected_settlements.append({

                "expected_settlement_id": (
                    f"EXP-{batch_id}"
                ),

                "batch_id": batch_id,

                "merchant_id": batch["merchant_id"],

                "processor_name": batch["processor_name"],

                "currency": currency,

                "expected_amount_minor": amount,

                "expected_date": expected_date.isoformat(),

                "status": "MISSING",

            })

            anomaly_counts["MISSING_DEPOSIT"] += 1

            continue

        # ------------------------------------------
        # NORMAL / ANOMALOUS DEPOSIT
        # ------------------------------------------

        actual_amount = amount
        actual_currency = currency
        anomaly_type = "NONE"

        if score < duplicate_limit:

            anomaly_type = "DUPLICATE_DEPOSIT"

        elif score < amount_limit:

            anomaly_type = "AMOUNT_MISMATCH"

            # Introduce a small discrepancy of 1–100
            # minor units, without changing the currency.
            discrepancy = (
                stable_number(f"{batch_id}|amount") % 100
            ) + 1

            actual_amount = amount - discrepancy

            if actual_amount == 0:
                actual_amount = amount + discrepancy

        elif score < currency_limit:

            anomaly_type = "CURRENCY_MISMATCH"

            # Use a different valid ISO currency code.
            alternatives = ["INR", "USD", "EUR", "GBP"]

            actual_currency = next(
                item
                for item in alternatives
                if item != currency
            )

        # ------------------------------------------
        # CREATE FIRST BANK ENTRY
        # ------------------------------------------

        bank_counter += 1

        bank_line_id = (
            f"BANK-2026-{bank_counter:06d}"
        )

        bank_timestamp = datetime.combine(
            expected_date,
            datetime.min.time(),
            tzinfo=timezone.utc
        ) + timedelta(hours=10)

        bank_lines.append({

            "bank_line_id": bank_line_id,

            "bank_name": BANK_NAME,

            "batch_reference": batch_id,

            "merchant_id": batch["merchant_id"],

            "transaction_type": (
                "CREDIT" if actual_amount > 0 else "DEBIT"
            ),

            "amount_minor": actual_amount,

            "currency": actual_currency,

            "transaction_timestamp": format_timestamp(
                bank_timestamp
            ),

            "description": (
                f"Settlement {batch_id}"
            ),

            "anomaly_type": anomaly_type,

        })

        if anomaly_type != "NONE":
            anomaly_counts[anomaly_type] += 1

        # ------------------------------------------
        # DUPLICATE BANK ENTRY
        # ------------------------------------------

        if anomaly_type == "DUPLICATE_DEPOSIT":

            bank_counter += 1

            duplicate_timestamp = (
                bank_timestamp + timedelta(minutes=2)
            )

            bank_lines.append({

                "bank_line_id": (
                    f"BANK-2026-{bank_counter:06d}"
                ),

                "bank_name": BANK_NAME,

                "batch_reference": batch_id,

                "merchant_id": batch["merchant_id"],

                "transaction_type": (
                    "CREDIT" if actual_amount > 0 else "DEBIT"
                ),

                "amount_minor": actual_amount,

                "currency": actual_currency,

                "transaction_timestamp": format_timestamp(
                    duplicate_timestamp
                ),

                "description": (
                    f"Duplicate settlement {batch_id}"
                ),

                "anomaly_type": "DUPLICATE_DEPOSIT",

            })

    # ----------------------------------------------
    # 3. VALIDATE BANK RECORDS
    # ----------------------------------------------

    print("Validating bank statement records...")

    bank_ids = [
        line["bank_line_id"]
        for line in bank_lines
    ]

    if len(bank_ids) != len(set(bank_ids)):
        raise ValueError("Duplicate bank line IDs found")

    for line in bank_lines:

        if int(line["amount_minor"]) == 0:
            raise ValueError(
                f"Zero-value bank entry: {line['bank_line_id']}"
            )

        if line["transaction_type"] not in [
            "CREDIT",
            "DEBIT"
        ]:
            raise ValueError("Invalid bank transaction type")

        if len(line["currency"]) != 3:
            raise ValueError("Invalid currency code")

    expected_batch_ids = {
        item["batch_id"]
        for item in expected_settlements
    }

    delayed_batch_ids = {
        batch["batch_id"]
        for batch in batches
        if batch["status"] == "DELAYED"
    }

    if not delayed_batch_ids.issubset(expected_batch_ids):
        raise ValueError(
            "A delayed settlement is missing from expected records"
        )

    # ----------------------------------------------
    # 4. EXPORT DATASETS
    # ----------------------------------------------

    write_csv(
        "bank_statement_lines.csv",
        bank_lines,
        [
            "bank_line_id",
            "bank_name",
            "batch_reference",
            "merchant_id",
            "transaction_type",
            "amount_minor",
            "currency",
            "transaction_timestamp",
            "description",
            "anomaly_type",
        ]
    )

    write_csv(
        "expected_settlements.csv",
        expected_settlements,
        [
            "expected_settlement_id",
            "batch_id",
            "merchant_id",
            "processor_name",
            "currency",
            "expected_amount_minor",
            "expected_date",
            "status",
        ]
    )

    # ----------------------------------------------
    # 5. SUMMARY
    # ----------------------------------------------

    print("\n" + "=" * 45)
    print("BANK GENERATION COMPLETED")
    print("=" * 45)

    print(f"Settlement batches : {len(batches):,}")
    print(f"Bank statement lines: {len(bank_lines):,}")
    print(f"Expected settlements: {len(expected_settlements):,}")

    print("\nAnomaly breakdown:")

    for anomaly, count in sorted(anomaly_counts.items()):
        print(f"{anomaly:25s}: {count:,}")

    print("\nValidation:")
    print("Bank line IDs       : VALID")
    print("Transaction types   : VALID")
    print("Currency formats    : VALID")
    print("Delayed tracking    : VALID")

    print("=" * 45)


# ==================================================
# ENTRY POINT
# ==================================================

if __name__ == "__main__":
    generate_bank_statements()
