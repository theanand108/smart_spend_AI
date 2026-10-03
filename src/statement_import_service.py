"""Persistence orchestration for statement imports.

Debit rows become normal SSAI Transaction records and therefore flow through
the existing V2 SQLAlchemy categorization hook. Credit rows deliberately bypass
that pipeline and are stored as received money only.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import inspect, text

from .intelligence.categorizer import categorize_transaction
from .statement_importer import ImportedTransaction, StatementImportResult


AUTO_RESOLVE_CONFIDENCE = 0.84


CREATE_RECEIVED_MONEY_SQL = """
CREATE TABLE IF NOT EXISTS received_money (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_date DATETIME NOT NULL,
    merchant_name VARCHAR(255) NOT NULL,
    amount FLOAT NOT NULL,
    source VARCHAR(50) NOT NULL,
    source_transaction_id VARCHAR(255),
    user_id INTEGER,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_RECEIVED_MONEY_UNIQUE_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS ux_received_money_source_transaction
ON received_money(source, source_transaction_id, user_id)
WHERE source_transaction_id IS NOT NULL
"""

CREATE_IMPORT_RECORDS_SQL = """
CREATE TABLE IF NOT EXISTS statement_import_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source VARCHAR(50) NOT NULL,
    source_transaction_id VARCHAR(255),
    direction VARCHAR(10) NOT NULL,
    transaction_id INTEGER,
    user_id INTEGER,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_IMPORT_RECORDS_UNIQUE_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS ux_statement_import_source_transaction
ON statement_import_records(source, source_transaction_id, user_id)
WHERE source_transaction_id IS NOT NULL
"""


def ensure_import_tables(session: Any) -> None:
    """Create the small import-only tables without changing Transaction."""
    session.execute(text(CREATE_RECEIVED_MONEY_SQL))
    session.execute(text(CREATE_IMPORT_RECORDS_SQL))

    # Flask-SQLAlchemy uses a scoped session whose legacy `.bind` attribute can
    # be unset even though the session is correctly connected to the app engine.
    # Resolve the active bind through SQLAlchemy instead of reading `.bind`.
    bind = session.get_bind()
    for table in ("received_money", "statement_import_records"):
        columns = {column["name"] for column in inspect(bind).get_columns(table)}
        if "user_id" not in columns:
            session.execute(text(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER"))

    # Rebuild import dedupe indexes so two users can import the same provider transaction.
    session.execute(text("DROP INDEX IF EXISTS ux_received_money_source_transaction"))
    session.execute(text("DROP INDEX IF EXISTS ux_statement_import_source_transaction"))
    session.execute(text(CREATE_RECEIVED_MONEY_UNIQUE_INDEX_SQL))
    session.execute(text(CREATE_IMPORT_RECORDS_UNIQUE_INDEX_SQL))
    session.flush()


def _already_imported(session: Any, item: ImportedTransaction, user_id: int | None) -> bool:
    if not item.source_transaction_id:
        return False
    result = session.execute(
        text(
            "SELECT 1 FROM statement_import_records "
            "WHERE source = :source AND source_transaction_id = :source_transaction_id "
            "AND user_id IS :user_id LIMIT 1"
        ),
        {
            "source": item.source,
            "source_transaction_id": item.source_transaction_id,
            "user_id": user_id,
        },
    ).first()
    return result is not None


def _record_import(
    session: Any,
    item: ImportedTransaction,
    transaction_id: int | None,
    user_id: int | None,
) -> None:
    session.execute(
        text(
            "INSERT INTO statement_import_records "
            "(source, source_transaction_id, direction, transaction_id, user_id) "
            "VALUES (:source, :source_transaction_id, :direction, :transaction_id, :user_id)"
        ),
        {
            "source": item.source,
            "source_transaction_id": item.source_transaction_id,
            "direction": item.direction,
            "transaction_id": transaction_id,
            "user_id": user_id,
        },
    )


def _store_received_money(session: Any, item: ImportedTransaction, user_id: int | None) -> None:
    """Store credit data only; no categorization or spending analytics."""
    session.execute(
        text(
            "INSERT INTO received_money "
            "(transaction_date, merchant_name, amount, source, source_transaction_id, user_id) "
            "VALUES (:transaction_date, :merchant_name, :amount, :source, :source_transaction_id, :user_id)"
        ),
        {
            "transaction_date": item.date,
            "merchant_name": item.merchant_name,
            "amount": item.amount,
            "source": item.source,
            "source_transaction_id": item.source_transaction_id,
            "user_id": user_id,
        },
    )


def reconcile_unresolved_transactions(
    session: Any,
    Transaction: Any,
    user_id: int | None = None,
) -> int:
    """Re-evaluate stored Unknown transactions against trusted user history.

    Imported rows are initially categorized oldest-first, so an early row cannot
    see later transactions from the same statement. This second pass fixes that
    limitation without retraining the global model or lowering its confidence
    gates: only a normal categorized decision at or above the existing
    high-confidence boundary is persisted.

    Unknown transactions are deliberately excluded from the history used for
    this pass. A newly auto-resolved row therefore cannot teach another row in
    the same pass, preventing uncertain data from cascading into false certainty.
    """
    query = session.query(Transaction)
    if hasattr(Transaction, "user_id"):
        if user_id is None:
            query = query.filter(Transaction.user_id.is_(None))
        else:
            query = query.filter(Transaction.user_id == user_id)

    rows = query.order_by(Transaction.date.asc(), Transaction.id.asc()).all()
    history = [
        {
            "merchant_name": row.merchant_name,
            "amount": row.amount,
            "category": row.category,
            "note": row.notes,
            "payment_method": row.payment_method,
        }
        for row in rows
        if row.category not in {None, "", "Unknown", "Others"}
    ]

    resolved = 0
    for transaction in rows:
        if transaction.category != "Unknown":
            continue

        result = categorize_transaction(
            merchant_name=transaction.merchant_name,
            amount=transaction.amount,
            note=transaction.notes,
            payment_method=transaction.payment_method,
            history=history,
            allow_personal_memory=True,
        )
        if (
            result.get("status") == "categorized"
            and result.get("category")
            and float(result.get("confidence") or 0.0) >= AUTO_RESOLVE_CONFIDENCE
        ):
            transaction._preserve_category_during_flush = True
            transaction.category = str(result["category"])
            resolved += 1

    if resolved:
        session.flush()

    return resolved

def import_statement(
    session: Any,
    Transaction: Any,
    result: StatementImportResult,
    user_id: int | None = None,
) -> dict[str, int]:
    """Persist a parsed statement using the existing V2 transaction path."""
    ensure_import_tables(session)

    imported_expenses = 0
    imported_received = 0
    skipped_duplicates = 0

    # Oldest first means later imported expenses can benefit from earlier rows
    # through the existing SQLAlchemy V2 history hook.
    for item in sorted(result.transactions, key=lambda transaction: transaction.date):
        if _already_imported(session, item, user_id):
            skipped_duplicates += 1
            continue

        if item.direction == "credit":
            _store_received_money(session, item, user_id)
            _record_import(session, item, None, user_id)
            imported_received += 1
            session.flush()
            continue

        transaction_kwargs = {
            "date": item.date,
            "merchant_name": item.merchant_name,
            "amount": item.amount,
            "notes": item.note,
            "payment_method": item.payment_method,
            "category": None,
        }
        if hasattr(Transaction, "user_id"):
            transaction_kwargs["user_id"] = user_id

        transaction = Transaction(**transaction_kwargs)
        session.add(transaction)
        # The existing persistence adapter runs before flush and resolves the
        # final V2 category. Each row is flushed before the next row so history
        # is available to subsequent imports.
        session.flush()
        _record_import(session, item, transaction.id, user_id)
        imported_expenses += 1

    # A complete statement can contain repeated entities/amounts that were not
    # visible when its earliest rows were categorized. Re-evaluate unresolved
    # rows once the full imported history is available.
    reconcile_unresolved_transactions(session, Transaction, user_id=user_id)

    session.commit()
    return {
        "imported_expenses": imported_expenses,
        "imported_received": imported_received,
        "skipped_duplicates": skipped_duplicates,
        "skipped_rows": len(result.skipped_rows),
    }
