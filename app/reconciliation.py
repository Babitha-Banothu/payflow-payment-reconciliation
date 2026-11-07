
import csv
import json
from collections import defaultdict, Counter
from datetime import datetime, timezone
from pathlib import Path


# ==================================================
# CONFIGURATION
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "generated"

SEED = 20261022


# ==================================================
# CSV UTILITIES
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


def write_csv(filename, records, columns):
    path = DATA_DIR / filename

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


def now_utc():
    return datetime.now(timezone.utc).isoformat()


# ==================================================
# EXCEPTION UTILITIES
# ==================================================

def create_exception(
    exceptions,
    exception_items,
    batch_id,
    issue_type,
    severity,
    description,
    settlement_lines,
    bank_line_id=None
):
    exception_number = len(exceptions) + 1

    exception_id = (
        f"EXC-2026-{exception_number:06d}"
    )

    detected_at = now_utc()

    exceptions.append({

        "exception_id": exception_id,

        "issue_type": issue_type,

        "severity": severity,

        "status": "OPEN",

        "description": description,

        "detected_at": detected_at,

        "batch_id": batch_id or "",

        "bank_line_id": bank_line_id or "",

    })

    # Attach settlement evidence to the exception.

    related_lines = settlement_lines.get(
        batch_id, []
    )

    item_number = len(exception_items) + 1

    if related_lines:

        for line in related_lines:

            exception_items.append({

                "exception_item_id": (
                    f"EXI-2026-{item_number:06d}"
                ),

                "exception_id": exception_id,

                "settlement_line_id": (
                    line["settlement_line_id"]
                ),

                "bank_line_id": bank_line_id or "",

                "source_type": "SETTLEMENT_LINE",

            })

            item_number += 1

    elif bank_line_id:

        exception_items.append({

            "exception_item_id": (
                f"EXI-2026-{item_number:06d}"
            ),

            "exception_id": exception_id,

            "settlement_line_id": "",

            "bank_line_id": bank_line_id,

            "source_type": "BANK_LINE",

        })


# ==================================================
# RECONCILIATION ENGINE
# ==================================================

def reconcile():

    print("\nPAYMENT RECONCILIATION ENGINE")
    print("=" * 50)

    # ----------------------------------------------
    # 1. LOAD INPUT DATA
    # ----------------------------------------------

    batches = read_csv("settlement_batches.csv")

    bank_lines = read_csv("bank_statement_lines.csv")

    expected = read_csv("expected_settlements.csv")

    settlement_line_records = read_csv(
        "settlement_lines.csv"
    )

    if not batches:
        raise ValueError("No settlement batches found")

    # ----------------------------------------------
    # 2. BUILD LOOKUP TABLES
    # ----------------------------------------------

    batch_lookup = {
        batch["batch_id"]: batch
        for batch in batches
    }

    if len(batch_lookup) != len(batches):
        raise ValueError("Duplicate settlement batch IDs")

    bank_ids = [
        line["bank_line_id"]
        for line in bank_lines
    ]

    if len(bank_ids) != len(set(bank_ids)):
        raise ValueError("Duplicate bank line IDs")

    expected_lookup = {
        item["batch_id"]: item
        for item in expected
    }

    if len(expected_lookup) != len(expected):
        raise ValueError("Duplicate expected settlement IDs")

    lines_by_batch = defaultdict(list)

    for line in settlement_line_records:

        lines_by_batch[line["batch_id"]].append(line)

    bank_by_reference = defaultdict(list)

    for line in bank_lines:

        bank_by_reference[
            line["batch_reference"]
        ].append(line)

    # ----------------------------------------------
    # 3. INITIALIZE OUTPUTS
    # ----------------------------------------------

    matches = []
    exceptions = []
    exception_items = []

    statistics = Counter()

    processed_bank_ids = set()

    match_counter = 0

    print("Matching bank entries to settlement batches...")

    # ----------------------------------------------
    # 4. RECONCILE EACH SETTLEMENT BATCH
    # ----------------------------------------------

    for batch_id in sorted(batch_lookup):

        batch = batch_lookup[batch_id]

        expected_amount = int(
            batch["net_amount_minor"]
        )

        expected_currency = batch["currency"]

        expected_merchant = batch["merchant_id"]

        matching_bank_lines = sorted(
            bank_by_reference.get(batch_id, []),
            key=lambda item: item["bank_line_id"]
        )

        # ------------------------------------------
        # DELAYED SETTLEMENT
        # ------------------------------------------

        if batch["status"] == "DELAYED":

            if matching_bank_lines:
                raise ValueError(
                    f"Delayed batch unexpectedly has a bank entry: {batch_id}"
                )

            match_counter += 1

            matches.append({

                "match_id": (
                    f"REC-2026-{match_counter:06d}"
                ),

                "batch_id": batch_id,

                "bank_line_id": "",

                "status": "UNMATCHED",

                "matching_method": "BATCH_REFERENCE",

                "expected_amount_minor": expected_amount,

                "actual_amount_minor": "",

                "expected_currency": expected_currency,

                "actual_currency": "",

                "amount_difference_minor": "",

                "confidence_score": 0,

                "created_at": now_utc(),

            })

            create_exception(
                exceptions,
                exception_items,
                batch_id,
                "DELAYED_SETTLEMENT",
                "MEDIUM",
                f"Settlement {batch_id} has not arrived at the bank.",
                lines_by_batch
            )

            statistics["DELAYED_SETTLEMENT"] += 1

            continue

        # ------------------------------------------
        # MISSING BANK DEPOSIT
        # ------------------------------------------

        if not matching_bank_lines:

            expected_record = expected_lookup.get(
                batch_id
            )

            if (
                expected_record
                and expected_record["status"] == "MISSING"
            ):
                issue_type = "UNMATCHED_SETTLEMENT"
                description = (
                    f"Expected settlement {batch_id} "
                    "has no corresponding bank deposit."
                )
                statistics["MISSING_SETTLEMENT"] += 1

            else:
                issue_type = "UNMATCHED_SETTLEMENT"
                description = (
                    f"No bank transaction found for settlement {batch_id}."
                )
                statistics["MISSING_SETTLEMENT"] += 1

            match_counter += 1

            matches.append({

                "match_id": (
                    f"REC-2026-{match_counter:06d}"
                ),

                "batch_id": batch_id,

                "bank_line_id": "",

                "status": "UNMATCHED",

                "matching_method": "BATCH_REFERENCE",

                "expected_amount_minor": expected_amount,

                "actual_amount_minor": "",

                "expected_currency": expected_currency,

                "actual_currency": "",

                "amount_difference_minor": "",

                "confidence_score": 0,

                "created_at": now_utc(),

            })

            create_exception(
                exceptions,
                exception_items,
                batch_id,
                issue_type,
                "HIGH",
                description,
                lines_by_batch
            )

            continue

        # ------------------------------------------
        # 5. PROCESS BANK ENTRIES
        # ------------------------------------------

        primary_bank_line = matching_bank_lines[0]

        actual_amount = int(
            primary_bank_line["amount_minor"]
        )

        actual_currency = primary_bank_line["currency"]

        actual_merchant = primary_bank_line["merchant_id"]

        actual_type = primary_bank_line["transaction_type"]

        expected_type = (
            "CREDIT"
            if expected_amount > 0
            else "DEBIT"
        )

        amount_difference = (
            actual_amount - expected_amount
        )

        issues = []

        if actual_currency != expected_currency:

            issues.append("CURRENCY_MISMATCH")

        if actual_amount != expected_amount:

            issues.append("AMOUNT_MISMATCH")

        if actual_merchant != expected_merchant:

            issues.append("MERCHANT_MISMATCH")

        if actual_type != expected_type:

            issues.append("TRANSACTION_TYPE_MISMATCH")

        # ------------------------------------------
        # 6. CLASSIFY PRIMARY MATCH
        # ------------------------------------------

        if not issues:

            match_status = "MATCHED"

            confidence = 1.0

            statistics["MATCHED"] += 1

        else:

            match_status = "PARTIAL"

            confidence = 0.5

            statistics["PARTIAL"] += 1

        match_counter += 1

        matches.append({

            "match_id": (
                f"REC-2026-{match_counter:06d}"
            ),

            "batch_id": batch_id,

            "bank_line_id": (
                primary_bank_line["bank_line_id"]
            ),

            "status": match_status,

            "matching_method": "BATCH_REFERENCE",

            "expected_amount_minor": expected_amount,

            "actual_amount_minor": actual_amount,

            "expected_currency": expected_currency,

            "actual_currency": actual_currency,

            "amount_difference_minor": amount_difference,

            "confidence_score": confidence,

            "created_at": now_utc(),

        })

        processed_bank_ids.add(
            primary_bank_line["bank_line_id"]
        )

        # ------------------------------------------
        # 7. CREATE FINANCIAL EXCEPTIONS
        # ------------------------------------------

        if "AMOUNT_MISMATCH" in issues:

            create_exception(
                exceptions,
                exception_items,
                batch_id,
                "AMOUNT_MISMATCH",
                "HIGH",
                (
                    f"Expected {expected_amount} {expected_currency}; "
                    f"received {actual_amount} {actual_currency}."
                ),
                lines_by_batch,
                primary_bank_line["bank_line_id"]
            )

            statistics["AMOUNT_MISMATCH"] += 1

        if "CURRENCY_MISMATCH" in issues:

            create_exception(
                exceptions,
                exception_items,
                batch_id,
                "CURRENCY_MISMATCH",
                "HIGH",
                (
                    f"Expected currency {expected_currency}; "
                    f"received {actual_currency}."
                ),
                lines_by_batch,
                primary_bank_line["bank_line_id"]
            )

            statistics["CURRENCY_MISMATCH"] += 1

        if "MERCHANT_MISMATCH" in issues:

            create_exception(
                exceptions,
                exception_items,
                batch_id,
                "UNMATCHED_BANK",
                "HIGH",
                (
                    f"Merchant mismatch for settlement {batch_id}."
                ),
                lines_by_batch,
                primary_bank_line["bank_line_id"]
            )

            statistics["MERCHANT_MISMATCH"] += 1

        if "TRANSACTION_TYPE_MISMATCH" in issues:

            create_exception(
                exceptions,
                exception_items,
                batch_id,
                "AMOUNT_MISMATCH",
                "HIGH",
                (
                    f"Incorrect bank transaction type for {batch_id}."
                ),
                lines_by_batch,
                primary_bank_line["bank_line_id"]
            )

            statistics["TRANSACTION_TYPE_MISMATCH"] += 1

        # ------------------------------------------
        # 8. DETECT DUPLICATE BANK DEPOSITS
        # ------------------------------------------

        for duplicate in matching_bank_lines[1:]:

            processed_bank_ids.add(
                duplicate["bank_line_id"]
            )

            match_counter += 1

            matches.append({

                "match_id": (
                    f"REC-2026-{match_counter:06d}"
                ),

                "batch_id": batch_id,

                "bank_line_id": duplicate["bank_line_id"],

                "status": "REJECTED",

                "matching_method": "DUPLICATE_REFERENCE",

                "expected_amount_minor": expected_amount,

                "actual_amount_minor": int(
                    duplicate["amount_minor"]
                ),

                "expected_currency": expected_currency,

                "actual_currency": duplicate["currency"],

                "amount_difference_minor": (
                    int(duplicate["amount_minor"])
                    - expected_amount
                ),

                "confidence_score": 0,

                "created_at": now_utc(),

            })

            create_exception(
                exceptions,
                exception_items,
                batch_id,
                "UNMATCHED_BANK",
                "HIGH",
                (
                    f"Duplicate bank transaction "
                    f"{duplicate['bank_line_id']} "
                    f"references settlement {batch_id}."
                ),
                lines_by_batch,
                duplicate["bank_line_id"]
            )

            statistics["DUPLICATE_BANK_ENTRY"] += 1

    # ----------------------------------------------
    # 9. DETECT UNMATCHED BANK RECORDS
    # ----------------------------------------------

    for bank_line in bank_lines:

        if bank_line["bank_line_id"] in processed_bank_ids:
            continue

        reference = bank_line["batch_reference"]

        create_exception(
            exceptions,
            exception_items,
            None,
            "UNMATCHED_BANK",
            "HIGH",
            (
                f"Bank transaction {bank_line['bank_line_id']} "
                f"references unknown settlement {reference}."
            ),
            lines_by_batch,
            bank_line["bank_line_id"]
        )

        statistics["UNMATCHED_BANK"] += 1

    # ----------------------------------------------
    # 10. VALIDATE OUTPUT
    # ----------------------------------------------

    print("Validating reconciliation results...")

    match_ids = [
        item["match_id"]
        for item in matches
    ]

    exception_ids = [
        item["exception_id"]
        for item in exceptions
    ]

    exception_item_ids = [
        item["exception_item_id"]
        for item in exception_items
    ]

    assert len(match_ids) == len(set(match_ids))
    assert len(exception_ids) == len(set(exception_ids))
    assert len(exception_item_ids) == len(set(exception_item_ids))

    # Every non-delayed batch must have a reconciliation result.
    assert len(matches) >= len(batches)

    # Every bank line must be accounted for by a match.
    matched_bank_ids = {
        item["bank_line_id"]
        for item in matches
        if item["bank_line_id"]
    }

    assert matched_bank_ids == set(bank_ids)

    # No bank line can be assigned to more than one match.
    assert len(matched_bank_ids) == sum(
        1
        for item in matches
        if item["bank_line_id"]
    )

    # Every exception item must reference an existing exception.
    known_exception_ids = set(exception_ids)

    assert all(
        item["exception_id"] in known_exception_ids
        for item in exception_items
    )

    # ----------------------------------------------
    # 11. EXPORT RECONCILIATION DATA
    # ----------------------------------------------

    write_csv(
        "reconciliation_matches.csv",
        matches,
        [
            "match_id",
            "batch_id",
            "bank_line_id",
            "status",
            "matching_method",
            "expected_amount_minor",
            "actual_amount_minor",
            "expected_currency",
            "actual_currency",
            "amount_difference_minor",
            "confidence_score",
            "created_at",
        ]
    )

    write_csv(
        "exceptions.csv",
        exceptions,
        [
            "exception_id",
            "issue_type",
            "severity",
            "status",
            "description",
            "detected_at",
            "batch_id",
            "bank_line_id",
        ]
    )

    write_csv(
        "exception_items.csv",
        exception_items,
        [
            "exception_item_id",
            "exception_id",
            "settlement_line_id",
            "bank_line_id",
            "source_type",
        ]
    )

    # ----------------------------------------------
    # 12. SUMMARY
    # ----------------------------------------------

    summary = {

        "seed": SEED,

        "total_settlement_batches": len(batches),

        "total_bank_statement_lines": len(bank_lines),

        "total_reconciliation_matches": len(matches),

        "total_exceptions": len(exceptions),

        "total_exception_items": len(exception_items),

        "match_status_counts": {
            status: sum(
                item["status"] == status
                for item in matches
            )
            for status in [
                "MATCHED",
                "PARTIAL",
                "UNMATCHED",
                "REJECTED"
            ]
        },

        "exception_counts": dict(
            sorted(statistics.items())
        ),

        "validation": "PASSED",

    }

    summary_path = (
        DATA_DIR / "reconciliation_summary.json"
    )

    with summary_path.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            summary,
            file,
            indent=4
        )

    print("Generated reconciliation_summary.json")

    # ----------------------------------------------
    # 13. DISPLAY RESULTS
    # ----------------------------------------------

    print("\n" + "=" * 50)
    print("RECONCILIATION COMPLETED")
    print("=" * 50)

    print(f"Settlement batches : {len(batches):,}")
    print(f"Bank statement lines: {len(bank_lines):,}")
    print(f"Reconciliation rows : {len(matches):,}")
    print(f"Exceptions          : {len(exceptions):,}")
    print(f"Exception items     : {len(exception_items):,}")

    print("\nMatch status:")

    for status, count in summary["match_status_counts"].items():
        print(f"{status:15s}: {count:,}")

    print("\nException breakdown:")

    for issue, count in sorted(statistics.items()):
        print(f"{issue:30s}: {count:,}")

    print("\nValidation:")
    print("Match IDs          : VALID")
    print("Exception IDs      : VALID")
    print("Exception references: VALID")
    print("Bank line coverage : VALID")
    print("Duplicate matching : VALID")

    print("=" * 50)


# ==================================================
# ENTRY POINT
# ==================================================

if __name__ == "__main__":
    reconcile()
