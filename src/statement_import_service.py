"""Persistence orchestration for statement imports.

Debit rows become normal SSAI Transaction records and therefore flow through
the existing V2 SQLAlchemy categorization hook. Credit rows deliberately bypass
the pipeline and are stored as received money only.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Column, DateTime, Float, Index, Integer, MetaData, String, Table, inspect, text

from .intelligence.categorizer import categorize_transaction
from .statement_importer import ImportedTransaction, StatementImportResult


AUTO_RESOLVE_CONFIDENCE = 0.84


def _import_tables() -> tuple[Table, Table]:
    """Build portable SQLAlchemy definitions for the import-only tables."""
    metadata = MetaData()
    received_money = Table(
        "received_money",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("transaction_date", DateTime, nullable=False),
        Column("merchant_name", String(255), nullable=False),
        Column("amount", Float, nullable=False),
        Column("source", String(50), nullable=False),
        Column("source_transaction_id", String(255)),
        Column("user_id", Integer),
        Column("created_at", DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    )
    statement_import_records = Table(
        "statement_import_records",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("source", String(50), nullable=False),
        Column("source_transaction_id", String(255)),
        Column("direction", String(10), nullable=False),
        Column("transaction_id", Integer),
        Column("user_id", Integer),
        Column("created_at", DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    )
    return received_money, statement_import_records


def _recreate_import_indexes(bind: Any) -> None:
    """Create user-scoped dedupe indexes using the active database dialect."""
    received_money, statement_import_records = _import_tables()

    for index_name in (
        "ux_received_money_source_transaction",
        "ux_statement_import_source_transaction",
    ):
        bind.exec_driver_sql(f"DROP INDEX IF EXISTS {index_name}")

    Index(
        "ux_received_money_source_transaction",
        received_money.c.source,
        received_money.c.source_transaction_id,
        received_money.c.user_id,
        unique=True,
        sqlite_where=received_money.c.source_transaction_id.is_not(None),
        postgresql_where=received_money.c.source_transaction_id.is_not(None),
    ).create(bind=bind)
    Index(
        "ux_statement_import_source_transaction",
        statement_import_records.c.source,
        statement_import_records.c.source_transaction_id,
        statement_import_records.c.user_id,
        unique=True,
        sqlite_where=statement_import_records.c.source_transaction_id.is_not(None),
        postgresql_where=statement_import_records.c.source_transaction_id.is_not(None),
    ).create(bind=bind)


def ensure_import_tables(session: Any) -> None:
    """Create or migrate the small import-only tables for SQLite/PostgreSQL."""
    bind = session.get_bind()
    received_money, statement_import_records = _import_tables()
    metadata = received_money.metadata
    metadata.create_all(bind=bind, tables=[received_money, statement_import_records], checkfirst=True)

    # Older beta databases may already have these tables without user_id.
    for table in ("received_money", "statement_import_records"):
        columns = {column["name"] for column in inspect(bind).get_columns(table)}
        if "user_id" not in columns:
            session.execute(text(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER"))

    # Rebuild the dedupe indexes so the same provider transaction is scoped to
    # the current user. The previous SQLite-only partial-index SQL is replaced
    # by SQLAlchemy-generated SQL for both supported database dialects.
    _recreate_import_indexes(bind)
    session.flush()


def _already_imported(session: Any, item: ImportedTransaction, user_id: int | None) -> bool:
    if not item.source_transaction_id:
        return False
    result = session.execute(
        text(
            "SELECT 1 FROM statement_import_records "
            "WHERE source = :source AND source_transaction_id = :source_transaction_id "
            "AND ((:user_id IS NULL AND user_id IS NULL) OR user_id = :user_id) "
            "LIMIT 1"
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
