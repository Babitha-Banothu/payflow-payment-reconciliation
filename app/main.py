import os
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

import psycopg
from fastapi import FastAPI, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


# --------------------------------------------------
# DATABASE CONFIGURATION
# --------------------------------------------------

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://payments_user:payments_pass@localhost:5432/payments_db",
)

DATABASE_URL = DATABASE_URL.replace(
    "postgresql+psycopg://",
    "postgresql://",
    1,
)


def get_connection():
    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
        connect_timeout=5,
    )


# --------------------------------------------------
# APPLICATION
# --------------------------------------------------

app = FastAPI(
    title="Payment Reconciliation API",
    description="Exception investigation and resolution API",
    version="1.0.0",
)


# --------------------------------------------------
# VALID VALUES
# --------------------------------------------------

VALID_STATUSES = {
    "OPEN",
    "INVESTIGATING",
    "RESOLVED",
    "REJECTED",
}

VALID_SEVERITIES = {
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
}

VALID_ISSUE_TYPES = {
    "AMOUNT_MISMATCH",
    "DUPLICATE_SETTLEMENT_LINE",
    "DUPLICATE_PROCESSOR_EVENT",
    "UNMATCHED_SETTLEMENT",
    "UNMATCHED_BANK",
    "CURRENCY_MISMATCH",
    "DELAYED_SETTLEMENT",
    "OUT_OF_ORDER_EVENT",
    "MISSING_RECORD",
}


# --------------------------------------------------
# REQUEST MODELS
# --------------------------------------------------

class InvestigationRequest(BaseModel):
    actor: str = Field(min_length=2, max_length=100)
    notes: str = Field(min_length=5, max_length=2000)


class ResolutionRequest(BaseModel):
    actor: str = Field(min_length=2, max_length=100)

    resolution_type: Literal[
        "AMOUNT_CORRECTED",
        "BANK_CONFIRMED",
        "DUPLICATE_CONFIRMED",
        "REFUND_ISSUED",
        "SETTLEMENT_CONFIRMED",
        "INVALID_EXCEPTION",
        "OTHER",
    ]

    notes: str = Field(min_length=5, max_length=2000)
    new_status: Literal["RESOLVED", "REJECTED"]


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def validate_filter(value, allowed, field_name):
    if value is not None and value not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name}: {value}",
        )


def fetch_exception(cursor, exception_id):
    cursor.execute(
        """
        SELECT
            e.exception_id,
            e.merchant_id,
            m.merchant_name,
            e.match_id,
            e.batch_id,
            e.bank_line_id,
            e.issue_type,
            e.severity,
            e.status,
            e.description,
            e.detected_at,
            e.resolved_at
        FROM exceptions e
        JOIN merchants m
            ON m.merchant_id = e.merchant_id
        WHERE e.exception_id = %s
        """,
        (exception_id,),
    )

    return cursor.fetchone()


def fetch_evidence(cursor, exception_id):
    cursor.execute(
        """
        SELECT
            ei.exception_item_id,
            ei.source_type,
            ei.settlement_line_id,

            sl.batch_id AS settlement_batch_id,
            sl.attempt_id AS settlement_attempt_id,
            sl.line_type,
            sl.currency AS settlement_currency,
            sl.signed_amount_minor,
            sl.fee_amount_minor,
            sl.net_amount_minor,

            ei.bank_line_id AS evidence_bank_line_id,
            b.bank_reference,
            b.bank_name,
            b.transaction_type,
            b.amount_minor AS bank_amount_minor,
            b.currency AS bank_currency,
            b.transaction_date,
            b.value_date,

            ei.processor_event_id,
            pe.event_type,
            pe.event_status,
            pe.event_timestamp,
            pe.processor_name,

            ei.delivery_id,
            ped.received_at AS delivery_received_at,
            ped.is_duplicate,

            ei.payment_attempt_id,
            pa.payment_id,
            pa.processor_reference,
            pa.status AS attempt_status

        FROM exception_items ei

        LEFT JOIN settlement_lines sl
            ON sl.settlement_line_id = ei.settlement_line_id

        LEFT JOIN bank_statement_lines b
            ON b.bank_line_id = ei.bank_line_id

        LEFT JOIN processor_events pe
            ON pe.event_id = ei.processor_event_id

        LEFT JOIN processor_event_deliveries ped
            ON ped.delivery_id = ei.delivery_id

        LEFT JOIN payment_attempts pa
            ON pa.attempt_id = ei.payment_attempt_id

        WHERE ei.exception_id = %s
        ORDER BY ei.exception_item_id
        """,
        (exception_id,),
    )

    return cursor.fetchall()


def jsonb_value(value):
    """Convert database values such as datetime into JSON-safe values."""
    return Jsonb(jsonable_encoder(value))


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/api/v1/health")
def health():
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 AS database_connected")
                result = cursor.fetchone()

        return {
            "status": "healthy",
            "database": result["database_connected"] == 1,
        }

    except psycopg.Error as exc:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        ) from exc


# --------------------------------------------------
# LIST EXCEPTIONS
# --------------------------------------------------

@app.get("/api/v1/exceptions")
def list_exceptions(
    status: str | None = None,
    severity: str | None = None,
    issue_type: str | None = None,
    merchant_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    validate_filter(status, VALID_STATUSES, "status")
    validate_filter(severity, VALID_SEVERITIES, "severity")
    validate_filter(issue_type, VALID_ISSUE_TYPES, "issue_type")

    conditions = []
    params = []

    if status:
        conditions.append("e.status = %s")
        params.append(status)

    if severity:
        conditions.append("e.severity = %s")
        params.append(severity)

    if issue_type:
        conditions.append("e.issue_type = %s")
        params.append(issue_type)

    if merchant_id:
        conditions.append("e.merchant_id = %s")
        params.append(merchant_id)

    where_clause = (
        "WHERE " + " AND ".join(conditions)
        if conditions
        else ""
    )

    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:

                cursor.execute(
                    f"""
                    SELECT COUNT(*) AS total
                    FROM exceptions e
                    {where_clause}
                    """,
                    params,
                )

                total = cursor.fetchone()["total"]

                cursor.execute(
                    f"""
                    SELECT
                        e.exception_id,
                        e.merchant_id,
                        m.merchant_name,
                        e.match_id,
                        e.batch_id,
                        e.bank_line_id,
                        e.issue_type,
                        e.severity,
                        e.status,
                        e.description,
                        e.detected_at,
                        e.resolved_at
                    FROM exceptions e
                    JOIN merchants m
                        ON m.merchant_id = e.merchant_id
                    {where_clause}
                    ORDER BY
                        CASE e.severity
                            WHEN 'CRITICAL' THEN 1
                            WHEN 'HIGH' THEN 2
                            WHEN 'MEDIUM' THEN 3
                            ELSE 4
                        END,
                        e.detected_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    params + [limit, offset],
                )

                items = cursor.fetchall()

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": items,
        }

    except psycopg.Error as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve exceptions",
        ) from exc


# --------------------------------------------------
# GET EXCEPTION DETAILS AND EVIDENCE
# --------------------------------------------------

@app.get("/api/v1/exceptions/{exception_id}")
def get_exception(exception_id: str):
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                exception = fetch_exception(cursor, exception_id)

                if not exception:
                    raise HTTPException(
                        status_code=404,
                        detail="Exception not found",
                    )

                evidence = fetch_evidence(cursor, exception_id)

        return {
            "exception": exception,
            "evidence": evidence,
        }

    except HTTPException:
        raise

    except psycopg.Error as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve exception details",
        ) from exc


# --------------------------------------------------
# START INVESTIGATION
# --------------------------------------------------

@app.post("/api/v1/exceptions/{exception_id}/investigate")
def investigate_exception(
    exception_id: str,
    request: InvestigationRequest,
):
    now = datetime.now(timezone.utc)

    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT *
                    FROM exceptions
                    WHERE exception_id = %s
                    FOR UPDATE
                    """,
                    (exception_id,),
                )

                exception = cursor.fetchone()

                if not exception:
                    raise HTTPException(
                        status_code=404,
                        detail="Exception not found",
                    )

                previous_status = exception["status"]

                if previous_status != "OPEN":
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Only OPEN exceptions can be moved "
                            "to INVESTIGATING"
                        ),
                    )

                old_state = dict(exception)

                cursor.execute(
                    """
                    UPDATE exceptions
                    SET status = 'INVESTIGATING'
                    WHERE exception_id = %s
                    RETURNING *
                    """,
                    (exception_id,),
                )

                updated = cursor.fetchone()

                cursor.execute(
                    """
                    INSERT INTO audit_events (
                        entity_type,
                        entity_id,
                        action,
                        old_state,
                        new_state,
                        actor,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        "EXCEPTION",
                        exception_id,
                        "INVESTIGATION_STARTED",
                        jsonb_value(old_state),
                        jsonb_value(dict(updated)),
                        request.actor,
                        now,
                    ),
                )

        return {
            "message": "Investigation started",
            "exception_id": exception_id,
            "previous_status": previous_status,
            "new_status": "INVESTIGATING",
            "notes": request.notes,
        }

    except HTTPException:
        raise

    except Exception as exc:
        print("INVESTIGATION ERROR:", repr(exc))
        raise HTTPException(
            status_code=500,
            detail="Unable to start investigation",
        ) from exc


# --------------------------------------------------
# RESOLVE EXCEPTION
# --------------------------------------------------

@app.post("/api/v1/exceptions/{exception_id}/resolve")
def resolve_exception(
    exception_id: str,
    request: ResolutionRequest,
):
    now = datetime.now(timezone.utc)

    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT *
                    FROM exceptions
                    WHERE exception_id = %s
                    FOR UPDATE
                    """,
                    (exception_id,),
                )

                exception = cursor.fetchone()

                if not exception:
                    raise HTTPException(
                        status_code=404,
                        detail="Exception not found",
                    )

                previous_status = exception["status"]

                if previous_status not in {"OPEN", "INVESTIGATING"}:
                    raise HTTPException(
                        status_code=409,
                        detail="Exception is already in a terminal state",
                    )

                old_state = dict(exception)

                cursor.execute(
                    """
                    UPDATE exceptions
                    SET
                        status = %s,
                        resolved_at = %s
                    WHERE exception_id = %s
                    RETURNING *
                    """,
                    (
                        request.new_status,
                        now,
                        exception_id,
                    ),
                )

                updated = cursor.fetchone()

                resolution_id = f"RES-{uuid4().hex[:16].upper()}"

                cursor.execute(
                    """
                    INSERT INTO resolutions (
                        resolution_id,
                        exception_id,
                        resolved_by,
                        resolution_type,
                        notes,
                        previous_status,
                        new_status,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        resolution_id,
                        exception_id,
                        request.actor,
                        request.resolution_type,
                        request.notes,
                        previous_status,
                        request.new_status,
                        now,
                    ),
                )

                cursor.execute(
                    """
                    INSERT INTO audit_events (
                        entity_type,
                        entity_id,
                        action,
                        old_state,
                        new_state,
                        actor,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        "EXCEPTION",
                        exception_id,
                        request.new_status,
                        jsonb_value(old_state),
                        jsonb_value(dict(updated)),
                        request.actor,
                        now,
                    ),
                )

        return {
            "message": "Exception status updated",
            "exception_id": exception_id,
            "resolution_id": resolution_id,
            "previous_status": previous_status,
            "new_status": request.new_status,
        }

    except HTTPException:
        raise

    except Exception as exc:
        print("RESOLUTION ERROR:", repr(exc))
        raise HTTPException(
            status_code=500,
            detail="Unable to resolve exception",
        ) from exc


# --------------------------------------------------
# EXCEPTION HISTORY
# --------------------------------------------------

@app.get("/api/v1/exceptions/{exception_id}/history")
def exception_history(exception_id: str):
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT exception_id
                    FROM exceptions
                    WHERE exception_id = %s
                    """,
                    (exception_id,),
                )

                if not cursor.fetchone():
                    raise HTTPException(
                        status_code=404,
                        detail="Exception not found",
                    )

                cursor.execute(
                    """
                    SELECT
                        resolution_id,
                        exception_id,
                        resolved_by,
                        resolution_type,
                        notes,
                        previous_status,
                        new_status,
                        created_at
                    FROM resolutions
                    WHERE exception_id = %s
                    ORDER BY created_at
                    """,
                    (exception_id,),
                )

                resolutions = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT
                        audit_id,
                        entity_type,
                        entity_id,
                        action,
                        old_state,
                        new_state,
                        actor,
                        created_at
                    FROM audit_events
                    WHERE entity_type = 'EXCEPTION'
                    AND entity_id = %s
                    ORDER BY created_at, audit_id
                    """,
                    (exception_id,),
                )

                audit_events = cursor.fetchall()

        return {
            "exception_id": exception_id,
            "resolutions": resolutions,
            "audit_events": audit_events,
        }

    except HTTPException:
        raise

    except psycopg.Error as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve exception history",
        ) from exc


    
# --------------------------------------------------
# TRANSACTIONS API
# --------------------------------------------------

@app.get("/api/v1/transactions")
def list_transactions(
    search: str | None = Query(default=None, max_length=150),
    status: str | None = Query(default=None),
    currency: str | None = Query(default=None, max_length=3),
    merchant_id: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    conditions = []
    params = []

    if search:
        conditions.append("""
            (
                p.payment_id ILIKE %s
                OR p.customer_reference ILIKE %s
                OR m.merchant_name ILIKE %s
                OR m.merchant_id ILIKE %s
            )
        """)
        term = f"%{search.strip()}%"
        params.extend([term, term, term, term])

    if status:
        conditions.append("UPPER(p.status) = UPPER(%s)")
        params.append(status)

    if currency:
        conditions.append("p.currency = UPPER(%s)")
        params.append(currency)

    if merchant_id:
        conditions.append("p.merchant_id = %s")
        params.append(merchant_id)

    if date_from:
        conditions.append("p.created_at >= %s::date")
        params.append(date_from)

    if date_to:
        conditions.append("p.created_at < (%s::date + INTERVAL '1 day')")
        params.append(date_to)

    where_clause = (
        "WHERE " + " AND ".join(conditions)
        if conditions else ""
    )

    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:

                # Overall transaction statistics
                cursor.execute("""
                    SELECT
                        COUNT(*) AS total,
                        COUNT(*) FILTER (
                            WHERE UPPER(status) IN ('SUCCESS', 'SUCCEEDED', 'CAPTURED', 'PAID')
                        ) AS successful,
                        COUNT(*) FILTER (
                            WHERE UPPER(status) IN ('FAILED', 'DECLINED')
                        ) AS failed,
                        COUNT(*) FILTER (
                            WHERE UPPER(status) IN ('PENDING', 'PROCESSING', 'CREATED')
                        ) AS pending
                    FROM payment_orders
                """)
                statistics = cursor.fetchone()

                # Status distribution
                cursor.execute("""
                    SELECT status, COUNT(*) AS count
                    FROM payment_orders
                    GROUP BY status
                    ORDER BY count DESC
                """)
                status_summary = cursor.fetchall()

                # Total records matching the filters
                cursor.execute(
                    f"""
                    SELECT COUNT(*) AS total
                    FROM payment_orders p
                    JOIN merchants m
                        ON m.merchant_id = p.merchant_id
                    {where_clause}
                    """,
                    params,
                )
                total = cursor.fetchone()["total"]

                # Paginated transaction records
                cursor.execute(
                    f"""
                    SELECT
                        p.payment_id,
                        p.merchant_id,
                        m.merchant_name,
                        p.customer_reference,
                        p.amount_minor,
                        p.currency,
                        p.status,
                        p.created_at,
                        p.updated_at,
                        COUNT(DISTINCT pa.attempt_id) AS attempt_count
                    FROM payment_orders p
                    JOIN merchants m
                        ON m.merchant_id = p.merchant_id
                    LEFT JOIN payment_attempts pa
                        ON pa.payment_id = p.payment_id
                    {where_clause}
                    GROUP BY
                        p.payment_id,
                        p.merchant_id,
                        m.merchant_name,
                        p.customer_reference,
                        p.amount_minor,
                        p.currency,
                        p.status,
                        p.created_at,
                        p.updated_at
                    ORDER BY p.created_at DESC, p.payment_id
                    LIMIT %s OFFSET %s
                    """,
                    params + [limit, offset],
                )
                items = cursor.fetchall()

        return {
            "statistics": statistics,
            "status_summary": status_summary,
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": items,
        }

    except psycopg.Error as exc:
        print(f"Transaction listing error: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve transactions",
        ) from exc


@app.get("/api/v1/transactions/{payment_id}")
def get_transaction(payment_id: str):
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:

                # Payment order and merchant
                cursor.execute(
                    """
                    SELECT
                        p.payment_id,
                        p.merchant_id,
                        m.merchant_name,
                        m.email AS merchant_email,
                        m.country AS merchant_country,
                        p.customer_reference,
                        p.amount_minor,
                        p.currency,
                        p.status,
                        p.created_at,
                        p.updated_at
                    FROM payment_orders p
                    JOIN merchants m
                        ON m.merchant_id = p.merchant_id
                    WHERE p.payment_id = %s
                    """,
                    (payment_id,),
                )
                payment = cursor.fetchone()

                if not payment:
                    raise HTTPException(
                        status_code=404,
                        detail="Payment transaction not found",
                    )

                # Payment attempts
                cursor.execute(
                    """
                    SELECT
                        attempt_id,
                        payment_id,
                        attempt_number,
                        processor_name,
                        processor_reference,
                        status,
                        attempted_at,
                        captured_at
                    FROM payment_attempts
                    WHERE payment_id = %s
                    ORDER BY attempt_number
                    """,
                    (payment_id,),
                )
                attempts = cursor.fetchall()

                # Processor events and delivery information
                cursor.execute(
                    """
                    SELECT
                        pe.event_id,
                        pe.attempt_id,
                        pe.processor_name,
                        pe.external_event_id,
                        pe.event_type,
                        pe.event_status,
                        pe.event_timestamp,
                        pe.received_at,
                        ped.delivery_id,
                        ped.is_duplicate,
                        ped.received_at AS delivery_received_at
                    FROM payment_attempts pa
                    JOIN processor_events pe
                        ON pe.attempt_id = pa.attempt_id
                    LEFT JOIN processor_event_deliveries ped
                        ON ped.event_id = pe.event_id
                    WHERE pa.payment_id = %s
                    ORDER BY pe.event_timestamp
                    """,
                    (payment_id,),
                )
                events = cursor.fetchall()

                # Refund records
                cursor.execute(
                    """
                    SELECT
                        refund_id,
                        payment_id,
                        attempt_id,
                        amount_minor,
                        currency,
                        status,
                        refund_timestamp
                    FROM refunds
                    WHERE payment_id = %s
                    ORDER BY refund_timestamp
                    """,
                    (payment_id,),
                )
                refunds = cursor.fetchall()

        return {
            "payment": payment,
            "attempts": attempts,
            "processor_events": events,
            "refunds": refunds,
        }

    except HTTPException:
        raise

    except psycopg.Error as exc:
        print(f"Transaction detail error: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve transaction details",
        ) from exc



# --------------------------------------------------
# RECONCILIATION API
# --------------------------------------------------

VALID_RECONCILIATION_STATUSES = {
    "MATCHED",
    "PARTIAL",
    "REJECTED",
    "UNMATCHED",
}


@app.get("/api/v1/reconciliation")
def list_reconciliation(
    search: str | None = Query(default=None, max_length=150),
    status: str | None = None,
    method: str | None = Query(default=None, max_length=80),
    merchant_id: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    validate_filter(
        status,
        VALID_RECONCILIATION_STATUSES,
        "status",
    )

    conditions = []
    params = []

    if status:
        conditions.append("r.status = %s")
        params.append(status)

    if method:
        conditions.append("r.matching_method = %s")
        params.append(method)

    if merchant_id:
        conditions.append("r.merchant_id = %s")
        params.append(merchant_id)

    if search:
        term = f"%{search.strip()}%"
        conditions.append("""
            (
                r.match_id ILIKE %s
                OR r.batch_id ILIKE %s
                OR r.bank_line_id ILIKE %s
                OR m.merchant_name ILIKE %s
                OR b.bank_reference ILIKE %s
                OR sb.processor_name ILIKE %s
            )
        """)
        params.extend([term] * 6)

    where_clause = (
        "WHERE " + " AND ".join(conditions)
        if conditions else ""
    )

    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:

                # Overall reconciliation statistics
                cursor.execute("""
                    SELECT
                        COUNT(*) AS total,
                        COUNT(*) FILTER (
                            WHERE status = 'MATCHED'
                        ) AS matched,
                        COUNT(*) FILTER (
                            WHERE status = 'PARTIAL'
                        ) AS partial,
                        COUNT(*) FILTER (
                            WHERE status = 'UNMATCHED'
                        ) AS unmatched,
                        COUNT(*) FILTER (
                            WHERE status = 'REJECTED'
                        ) AS rejected,
                        COALESCE(
                            SUM(ABS(variance_minor)),
                            0
                        ) AS total_absolute_variance_minor,
                        ROUND(
                            AVG(confidence_score),
                            4
                        ) AS average_confidence
                    FROM reconciliation_matches
                """)
                statistics = cursor.fetchone()

                # Status distribution
                cursor.execute("""
                    SELECT
                        status,
                        COUNT(*) AS count
                    FROM reconciliation_matches
                    GROUP BY status
                    ORDER BY count DESC
                """)
                status_summary = cursor.fetchall()

                # Matching method distribution
                cursor.execute("""
                    SELECT
                        matching_method,
                        COUNT(*) AS count
                    FROM reconciliation_matches
                    GROUP BY matching_method
                    ORDER BY count DESC
                """)
                method_summary = cursor.fetchall()

                # Filtered record count
                cursor.execute(
                    f"""
                    SELECT COUNT(*) AS total
                    FROM reconciliation_matches r
                    JOIN merchants m
                        ON m.merchant_id = r.merchant_id
                    LEFT JOIN bank_statement_lines b
                        ON b.bank_line_id = r.bank_line_id
                    LEFT JOIN settlement_batches sb
                        ON sb.batch_id = r.batch_id
                    {where_clause}
                    """,
                    params,
                )
                total = cursor.fetchone()["total"]

                # Paginated reconciliation records
                cursor.execute(
                    f"""
                    SELECT
                        r.match_id,
                        r.merchant_id,
                        m.merchant_name,
                        r.status,
                        r.matching_method,
                        r.expected_amount_minor,
                        r.actual_amount_minor,
                        r.variance_minor,
                        r.currency,
                        r.confidence_score,
                        r.matched_at,
                        r.batch_id,
                        r.bank_line_id,
                        sb.processor_name,
                        sb.settlement_date,
                        b.bank_reference,
                        (
                            SELECT COUNT(*)
                            FROM reconciliation_match_items mi
                            WHERE mi.match_id = r.match_id
                        ) AS line_count
                    FROM reconciliation_matches r
                    JOIN merchants m
                        ON m.merchant_id = r.merchant_id
                    LEFT JOIN settlement_batches sb
                        ON sb.batch_id = r.batch_id
                    LEFT JOIN bank_statement_lines b
                        ON b.bank_line_id = r.bank_line_id
                    {where_clause}
                    ORDER BY r.matched_at DESC NULLS LAST,
                             r.match_id
                    LIMIT %s OFFSET %s
                    """,
                    params + [limit, offset],
                )
                items = cursor.fetchall()

        return {
            "statistics": statistics,
            "status_summary": status_summary,
            "method_summary": method_summary,
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": items,
        }

    except psycopg.Error as exc:
        print("RECONCILIATION LIST ERROR:", repr(exc))
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve reconciliation records",
        ) from exc


@app.get("/api/v1/reconciliation/{match_id}")
def get_reconciliation_details(match_id: str):
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:

                # Main match and merchant details
                cursor.execute(
                    """
                    SELECT
                        r.match_id,
                        r.merchant_id,
                        m.merchant_name,
                        m.email AS merchant_email,
                        m.country AS merchant_country,
                        r.status,
                        r.matching_method,
                        r.expected_amount_minor,
                        r.actual_amount_minor,
                        r.variance_minor,
                        r.currency,
                        r.confidence_score,
                        r.matched_at,
                        r.batch_id,
                        r.bank_line_id
                    FROM reconciliation_matches r
                    JOIN merchants m
                        ON m.merchant_id = r.merchant_id
                    WHERE r.match_id = %s
                    """,
                    (match_id,),
                )
                match = cursor.fetchone()

                if not match:
                    raise HTTPException(
                        status_code=404,
                        detail="Reconciliation match not found",
                    )

                # Settlement batch
                cursor.execute(
                    """
                    SELECT
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
                    FROM settlement_batches
                    WHERE batch_id = %s
                    """,
                    (match["batch_id"],),
                )
                batch = cursor.fetchone()

                # Related bank statement line
                cursor.execute(
                    """
                    SELECT
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
                    FROM bank_statement_lines
                    WHERE bank_line_id = %s
                    """,
                    (match["bank_line_id"],),
                )
                bank_line = cursor.fetchone()

                # Settlement lines allocated to this match
                cursor.execute(
                    """
                    SELECT
                        mi.match_item_id,
                        mi.match_id,
                        mi.allocated_amount_minor,
                        sl.settlement_line_id,
                        sl.batch_id,
                        sl.attempt_id,
                        sl.line_type,
                        sl.currency,
                        sl.signed_amount_minor,
                        sl.fee_amount_minor,
                        sl.net_amount_minor,
                        sl.created_at
                    FROM reconciliation_match_items mi
                    JOIN settlement_lines sl
                        ON sl.settlement_line_id =
                           mi.settlement_line_id
                    WHERE mi.match_id = %s
                    ORDER BY mi.match_item_id
                    """,
                    (match_id,),
                )
                settlement_lines = cursor.fetchall()

        return {
            "match": match,
            "batch": batch,
            "bank_line": bank_line,
            "settlement_lines": settlement_lines,
        }

    except HTTPException:
        raise

    except psycopg.Error as exc:
        print("RECONCILIATION DETAIL ERROR:", repr(exc))
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve reconciliation details",
        ) from exc



# ==============================
# REPORTS & ANALYTICS API
# ==============================

@app.get("/api/v1/reports/overview")
def get_reports_overview():
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:

                # Transaction summary by currency
                cursor.execute("""
                    SELECT
                        currency,
                        COUNT(*) AS total_transactions,
                        COUNT(*) FILTER (
                            WHERE UPPER(status) IN (
                                'SUCCESS',
                                'SUCCEEDED',
                                'CAPTURED',
                                'PAID'
                            )
                        ) AS successful,
                        COUNT(*) FILTER (
                            WHERE UPPER(status) IN (
                                'FAILED',
                                'DECLINED'
                            )
                        ) AS failed,
                        COUNT(*) FILTER (
                            WHERE UPPER(status) IN (
                                'PENDING',
                                'PROCESSING',
                                'CREATED'
                            )
                        ) AS pending,
                        COALESCE(SUM(amount_minor), 0)
                            AS total_amount_minor
                    FROM payment_orders
                    GROUP BY currency
                    ORDER BY currency
                """)
                transaction_summary = cursor.fetchall()

                # Transaction status distribution
                cursor.execute("""
                    SELECT
                        status,
                        COUNT(*) AS count
                    FROM payment_orders
                    GROUP BY status
                    ORDER BY count DESC
                """)
                transaction_status = cursor.fetchall()

                # Reconciliation summary
                cursor.execute("""
                    SELECT
                        status,
                        COUNT(*) AS count,
                        COALESCE(
                            SUM(ABS(variance_minor)),
                            0
                        ) AS absolute_variance_minor
                    FROM reconciliation_matches
                    GROUP BY status
                    ORDER BY count DESC
                """)
                reconciliation_summary = cursor.fetchall()

                # Exception summary
                cursor.execute("""
                    SELECT
                        status,
                        severity,
                        COUNT(*) AS count
                    FROM exceptions
                    GROUP BY status, severity
                    ORDER BY status, severity
                """)
                exception_summary = cursor.fetchall()

                # Daily transaction volume for the last 30 days
                cursor.execute("""
                    SELECT
                        DATE(created_at) AS transaction_date,
                        currency,
                        COUNT(*) AS transaction_count
                    FROM payment_orders
                    WHERE created_at >= CURRENT_DATE - INTERVAL '29 days'
                    GROUP BY DATE(created_at), currency
                    ORDER BY transaction_date, currency
                """)
                daily_transactions = cursor.fetchall()

        return {
            "transaction_summary": transaction_summary,
            "transaction_status": transaction_status,
            "reconciliation_summary": reconciliation_summary,
            "exception_summary": exception_summary,
            "daily_transactions": daily_transactions,
        }

    except psycopg.Error as exc:
        print("REPORTS API ERROR:", repr(exc))
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve reports",
        ) from exc

# ==============================
# AUDIT HISTORY API
# ==============================

@app.get("/api/v1/audit")
def get_audit_history(
    search: str = Query(default="", max_length=150),
    entity_type: str = Query(default=""),
    action: str = Query(default=""),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    conditions = []
    params = []

    # Search across audit ID, entity, actor and action
    search = search.strip()

    if search:
        conditions.append("""
            (
                CAST(audit_id AS TEXT) ILIKE %s
                OR entity_id ILIKE %s
                OR actor ILIKE %s
                OR action ILIKE %s
                OR entity_type ILIKE %s
            )
        """)
        term = f"%{search}%"
        params.extend([term] * 5)

    if entity_type:
        conditions.append("entity_type = %s")
        params.append(entity_type)

    if action:
        conditions.append("action = %s")
        params.append(action)

    where_clause = (
        "WHERE " + " AND ".join(conditions)
        if conditions
        else ""
    )

    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:

                # Total matching audit records
                cursor.execute(
                    f"""
                    SELECT COUNT(*) AS total
                    FROM audit_events
                    {where_clause}
                    """,
                    params,
                )
                total = cursor.fetchone()["total"]

                # Paginated audit records
                cursor.execute(
                    f"""
                    SELECT
                        audit_id,
                        entity_type,
                        entity_id,
                        action,
                        old_state,
                        new_state,
                        actor,
                        created_at
                    FROM audit_events
                    {where_clause}
                    ORDER BY created_at DESC, audit_id DESC
                    LIMIT %s OFFSET %s
                    """,
                    params + [limit, offset],
                )
                items = cursor.fetchall()

                # Entity type statistics
                cursor.execute("""
                    SELECT
                        entity_type,
                        COUNT(*) AS count
                    FROM audit_events
                    GROUP BY entity_type
                    ORDER BY count DESC
                """)
                entity_summary = cursor.fetchall()

                # Action statistics
                cursor.execute("""
                    SELECT
                        action,
                        COUNT(*) AS count
                    FROM audit_events
                    GROUP BY action
                    ORDER BY count DESC
                """)
                action_summary = cursor.fetchall()

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": items,
            "entity_summary": entity_summary,
            "action_summary": action_summary,
        }

    except psycopg.Error as exc:
        print("AUDIT HISTORY ERROR:", repr(exc))
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve audit history",
        ) from exc



