"""Persistence orchestration for statement imports.

Debit rows become normal SSAI Transaction records and therefore flow through
the existing V2 SQLAlchemy categorization hook. Credit rows deliberately bypass
that pipeline and are stored as received money only.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from .statement_importer import ImportedTransaction, StatementImportResult


CREATE_RECEIVED_MONEY_SQL = """
CREATE TABLE IF NOT EXISTS received_money (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_date DATETIME NOT NULL,
    merchant_name VARCHAR(255) NOT NULL,
    amount FLOAT NOT NULL,
    source VARCHAR(50) NOT NULL,
    source_transaction_id VARCHAR(255),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_RECEIVED_MONEY_UNIQUE_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS ux_received_money_source_transaction
ON received_money(source, source_transaction_id)
WHERE source_transaction_id IS NOT NULL
"""

CREATE_IMPORT_RECORDS_SQL = """
CREATE TABLE IF NOT EXISTS statement_import_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source VARCHAR(50) NOT NULL,
    source_transaction_id VARCHAR(255),
    direction VARCHAR(10) NOT NULL,
    transaction_id INTEGER,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_IMPORT_RECORDS_UNIQUE_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS ux_statement_import_source_transaction
ON statement_import_records(source, source_transaction_id)
WHERE source_transaction_id IS NOT NULL
"""


def ensure_import_tables(session: Any) -> None:
    """Create the small import-only tables without changing Transaction."""
    session.execute(text(CREATE_RECEIVED_MONEY_SQL))
    session.execute(text(CREATE_RECEIVED_MONEY_UNIQUE_INDEX_SQL))
    session.execute(text(CREATE_IMPORT_RECORDS_SQL))
    session.execute(text(CREATE_IMPORT_RECORDS_UNIQUE_INDEX_SQL))
    session.flush()


def _already_imported(session: Any, item: ImportedTransaction) -> bool:
    if not item.source_transaction_id:
        return False
    result = session.execute(
        text(
            "SELECT 1 FROM statement_import_records "
            "WHERE source = :source AND source_transaction_id = :source_transaction_id LIMIT 1"
        ),
        {
            "source": item.source,
            "source_transaction_id": item.source_transaction_id,
        },
    ).first()
    return result is not None


def _record_import(
    session: Any,
    item: ImportedTransaction,
    transaction_id: int | None,
) -> None:
    session.execute(
        text(
            "INSERT INTO statement_import_records "
            "(source, source_transaction_id, direction, transaction_id) "
            "VALUES (:source, :source_transaction_id, :direction, :transaction_id)"
        ),
        {
            "source": item.source,
            "source_transaction_id": item.source_transaction_id,
            "direction": item.direction,
            "transaction_id": transaction_id,
        },
    )


def _store_received_money(session: Any, item: ImportedTransaction) -> None:
    """Store credit data only; no categorization or spending analytics."""
    session.execute(
        text(
            "INSERT INTO received_money "
            "(transaction_date, merchant_name, amount, source, source_transaction_id) "
            "VALUES (:transaction_date, :merchant_name, :amount, :source, :source_transaction_id)"
        ),
        {
            "transaction_date": item.date,
            "merchant_name": item.merchant_name,
            "amount": item.amount,
            "source": item.source,
            "source_transaction_id": item.source_transaction_id,
        },
    )


def import_statement(
    session: Any,
    Transaction: Any,
    result: StatementImportResult,
) -> dict[str, int]:
    """Persist a parsed statement using the existing V2 transaction path."""
    ensure_import_tables(session)

    imported_expenses = 0
    imported_received = 0
    skipped_duplicates = 0

    # Oldest first means later imported expenses can benefit from earlier rows
    # through the existing SQLAlchemy V2 history hook.
    for item in sorted(result.transactions, key=lambda transaction: transaction.date):
        if _already_imported(session, item):
            skipped_duplicates += 1
            continue

        if item.direction == "credit":
            _store_received_money(session, item)
            _record_import(session, item, None)
            imported_received += 1
            session.flush()
            continue

        transaction = Transaction(
            date=item.date,
            merchant_name=item.merchant_name,
            amount=item.amount,
            notes=item.note,
            payment_method=item.payment_method,
            category=None,
        )
        session.add(transaction)
        # The existing persistence adapter runs before flush and resolves the
        # final V2 category. Each row is flushed before the next row so history
        # is available to subsequent imports.
        session.flush()
        _record_import(session, item, transaction.id)
        imported_expenses += 1

    session.commit()
    return {
        "imported_expenses": imported_expenses,
        "imported_received": imported_received,
        "skipped_duplicates": skipped_duplicates,
        "skipped_rows": len(result.skipped_rows),
    }
