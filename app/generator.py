
import argparse
import csv
import hashlib
import json
import random

from datetime import datetime, timedelta, timezone
from pathlib import Path

from faker import Faker


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

SEED = 20261022

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "generated"

BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)

rng = random.Random(SEED)

fake = Faker()
fake.seed_instance(SEED)


COUNTRIES = {
    "IN": "INR",
    "US": "USD",
    "GB": "GBP",
    "DE": "EUR",
}

PROCESSORS = [
    "STRIPE_SIM",
    "RAZORPAY_SIM",
    "ADYEN_SIM",
]


# --------------------------------------------------
# UTILITY FUNCTIONS
# --------------------------------------------------

def make_timestamp(base_date, minutes=0):
    seconds = rng.randint(0, 59)

    value = base_date + timedelta(
        minutes=minutes,
        seconds=seconds
    )

    return value.isoformat()


def generate_amount():
    return rng.choice([
        49900,
        99900,
        149900,
        199900,
        249900,
        499900,
        999900,
        rng.randint(10000, 5000000),
    ])


def generate_hash(value):
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def write_csv(filename, records):
    path = OUTPUT_DIR / filename

    if not records:
        path.write_text("", encoding="utf-8")
        print(f"Generated {filename}: 0 rows")
        return

    with path.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=list(records[0].keys())
        )

        writer.writeheader()
        writer.writerows(records)

    print(f"Generated {filename}: {len(records):,} rows")


# --------------------------------------------------
# 1. MERCHANT GENERATION
# --------------------------------------------------

def generate_merchants(count):

    merchants = []

    for i in range(1, count + 1):

        country = rng.choice(
            list(COUNTRIES.keys())
        )

        merchants.append({

            "merchant_id": f"MER-2026-{i:06d}",

            "merchant_name": fake.company(),

            "email": f"merchant{i}@example.test",

            "country": country,

            "default_currency": COUNTRIES[country],

            "status": rng.choices(
                ["ACTIVE", "INACTIVE", "SUSPENDED"],
                weights=[95, 3, 2]
            )[0],

            "created_at": (
                BASE_TIME - timedelta(days=1)
            ).isoformat(),

        })

    return merchants


# --------------------------------------------------
# 2. PAYMENT ORDERS
# 3. PAYMENT ATTEMPTS
# 4. PROCESSOR EVENTS
# 5. WEBHOOK DELIVERIES
# --------------------------------------------------

def generate_payments(merchants, order_count):

    orders = []
    attempts = []
    events = []
    deliveries = []

    retry_count = round(order_count * 0.10)

    retry_orders = set(
        rng.sample(
            range(1, order_count + 1),
            retry_count
        )
    )

    event_counter = 0
    delivery_counter = 0

    for i in range(1, order_count + 1):

        payment_id = f"PAY-2026-{i:08d}"

        merchant = rng.choice(merchants)

        order_amount = generate_amount()

        currency = merchant["default_currency"]

        processor = rng.choice(PROCESSORS)

        order_date = rng.randint(0, 300)

        order_created = (
            BASE_TIME
            + timedelta(
                days=order_date,
                seconds=rng.randint(0, 3600)
            )
        )

        number_of_attempts = (
            2 if i in retry_orders else 1
        )

        order_attempt_statuses = []

        # Generate attempts for this payment.

        for attempt_number in range(
            1,
            number_of_attempts + 1
        ):

            attempt_id = (
                f"ATT-{payment_id}-{attempt_number:02d}"
            )

            attempted_at_dt = (
                order_created
                + timedelta(minutes=attempt_number * 10)
            )

            attempted_at = attempted_at_dt.isoformat()

            # First attempt in a retry scenario fails.
            if number_of_attempts == 2 and attempt_number == 1:

                status = "FAILED"

            else:

                status = rng.choices(
                    ["CAPTURED", "FAILED"],
                    weights=[85, 15]
                )[0]

            captured_at = None

            if status == "CAPTURED":

                captured_at = (
                    attempted_at_dt
                    + timedelta(minutes=5)
                ).isoformat()

            processor_reference = (
                f"PR-{i:08d}-{attempt_number:02d}"
            )

            attempts.append({

                "attempt_id": attempt_id,

                "payment_id": payment_id,

                "attempt_number": attempt_number,

                "processor_name": processor,

                "processor_reference": processor_reference,

                "status": status,

                "attempted_at": attempted_at,

                "captured_at": captured_at,

            })

            order_attempt_statuses.append(status)

            # Generate processor events.

            event_types = ["INITIATED"]

            if status == "CAPTURED":

                event_types.extend([
                    "AUTHORIZED",
                    "CAPTURED"
                ])

            else:

                event_types.append("FAILED")

            for event_index, event_type in enumerate(event_types):

                event_counter += 1

                event_id = (
                    f"EVT-2026-{event_counter:010d}"
                )

                event_time = (
                    attempted_at_dt
                    + timedelta(seconds=event_index * 30)
                )

                event_timestamp = event_time.isoformat()

                event_hash = generate_hash(
                    f"{attempt_id}|{event_type}|{event_timestamp}"
                )

                events.append({

                    "event_id": event_id,

                    "attempt_id": attempt_id,

                    "processor_name": processor,

                    "external_event_id": event_id,

                    "event_type": event_type,

                    "event_status": "PROCESSED",

                    "event_timestamp": event_timestamp,

                    "received_at": (
                        event_time + timedelta(seconds=5)
                    ).isoformat(),

                    "payload_hash": event_hash,

                })

                # Original webhook delivery.

                delivery_counter += 1

                deliveries.append({

                    "delivery_id": (
                        f"DLV-2026-{delivery_counter:010d}"
                    ),

                    "event_id": event_id,

                    "received_at": (
                        event_time + timedelta(seconds=5)
                    ).isoformat(),

                    "payload_hash": event_hash,

                    "is_duplicate": False,

                })

                # Simulate occasional duplicate webhook delivery.

                if rng.random() < 0.01:

                    delivery_counter += 1

                    deliveries.append({

                        "delivery_id": (
                            f"DLV-2026-{delivery_counter:010d}"
                        ),

                        "event_id": event_id,

                        "received_at": (
                            event_time + timedelta(days=1)
                        ).isoformat(),

                        "payload_hash": event_hash,

                        "is_duplicate": True,

                    })

        # Derive order status from its attempts.

        final_status = (
            "PAID"
            if "CAPTURED" in order_attempt_statuses
            else "FAILED"
        )

        orders.append({

            "payment_id": payment_id,

            "merchant_id": merchant["merchant_id"],

            "customer_reference": f"CUST-REF-{i:08d}",

            "amount_minor": order_amount,

            "currency": currency,

            "status": final_status,

            "created_at": order_created.isoformat(),

            "updated_at": (
                order_created + timedelta(days=2)
            ).isoformat(),

        })

    return orders, attempts, events, deliveries


# --------------------------------------------------
# 6. DATA VALIDATION
# --------------------------------------------------

def validate_data(merchants, orders, attempts, events, deliveries):

    merchant_ids = {
        m["merchant_id"] for m in merchants
    }

    payment_ids = {
        p["payment_id"] for p in orders
    }

    attempt_ids = {
        a["attempt_id"] for a in attempts
    }

    event_ids = {
        e["event_id"] for e in events
    }

    # Primary key uniqueness.

    assert len(merchant_ids) == len(merchants)

    assert len(payment_ids) == len(orders)

    assert len(attempt_ids) == len(attempts)

    assert len(event_ids) == len(events)

    # Foreign key validation.

    assert all(
        p["merchant_id"] in merchant_ids
        for p in orders
    )

    assert all(
        a["payment_id"] in payment_ids
        for a in attempts
    )

    assert all(
        e["attempt_id"] in attempt_ids
        for e in events
    )

    assert all(
        d["event_id"] in event_ids
        for d in deliveries
    )

    # Financial and lifecycle validation.

    assert all(
        p["amount_minor"] > 0
        for p in orders
    )

    assert all(
        a["status"] in [
            "INITIATED",
            "AUTHORIZED",
            "CAPTURED",
            "FAILED",
            "CANCELLED"
        ]
        for a in attempts
    )

    assert all(
        a["captured_at"] is None
        or a["captured_at"] >= a["attempted_at"]
        for a in attempts
    )

    assert all(
        e["event_status"] in [
            "RECEIVED",
            "PROCESSED",
            "REJECTED"
        ]
        for e in events
    )

    print("\n========== VALIDATION PASSED ==========")

    print(f"Merchants: {len(merchants):,}")

    print(f"Payment orders: {len(orders):,}")

    print(f"Payment attempts: {len(attempts):,}")

    print(f"Processor events: {len(events):,}")

    print(f"Webhook deliveries: {len(deliveries):,}")

    print("Primary keys: VALID")

    print("Foreign keys: VALID")

    print("Lifecycle timestamps: VALID")

    print("=======================================\n")


# --------------------------------------------------
# 7. MAIN GENERATOR
# --------------------------------------------------

def main(scale):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    merchant_count = max(
        1,
        round(2000 * scale)
    )

    order_count = max(
        10,
        round(50000 * scale)
    )

    print("\nPAYMENT RECONCILIATION DATA GENERATOR")

    print("-------------------------------------")

    print(f"Random seed: {SEED}")

    print(f"Dataset scale: {scale}")

    print(f"Merchants target: {merchant_count:,}")

    print(f"Payment orders target: {order_count:,}")

    print("\nGenerating merchants...")

    merchants = generate_merchants(
        merchant_count
    )

    print("Generating payments and processor events...")

    orders, attempts, events, deliveries = (
        generate_payments(
            merchants,
            order_count
        )
    )

    print("Validating generated records...")

    validate_data(
        merchants,
        orders,
        attempts,
        events,
        deliveries
    )

    print("Exporting CSV files...")

    write_csv("merchants.csv", merchants)

    write_csv("payment_orders.csv", orders)

    write_csv("payment_attempts.csv", attempts)

    write_csv("processor_events.csv", events)

    write_csv(
        "processor_event_deliveries.csv",
        deliveries
    )

    manifest = {

        "project": "Payment Reconciliation System",

        "seed": SEED,

        "scale": scale,

        "dataset_version": "1.0",

        "row_counts": {

            "merchants": len(merchants),

            "payment_orders": len(orders),

            "payment_attempts": len(attempts),

            "processor_events": len(events),

            "processor_event_deliveries": len(deliveries),

        }

    }

    with (
        OUTPUT_DIR / "manifest.json"
    ).open("w", encoding="utf-8") as file:

        json.dump(
            manifest,
            file,
            indent=4
        )

    print("\nDATA GENERATION COMPLETED SUCCESSFULLY!")

    print(f"Output directory: {OUTPUT_DIR}")


# --------------------------------------------------
# COMMAND LINE ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Synthetic Payment Data Generator"
    )

    parser.add_argument(
        "--scale",
        type=float,
        default=0.02,
        help="Dataset scale: 0.02 starter, 1.0 full"
    )

    args = parser.parse_args()

    if not 0 < args.scale <= 1:

        parser.error(
            "Scale must be greater than 0 and at most 1"
        )

    main(args.scale)
