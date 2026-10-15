"""Application persistence adapter for transaction intelligence V2.

The Flask application currently owns the Transaction model and historically
assigned categories directly in its routes. This adapter keeps that application
surface unchanged while making the V2 categorizer the authoritative category
resolver at the SQLAlchemy persistence boundary.

Only an accepted V2 decision is persisted as a concrete category. Decisions
that require confirmation, conflict, vary, or abstain are persisted as
``Unknown`` so the application never turns an uncertain candidate into false
certainty.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import Session

from .categorizer import categorize_transaction
from sqlalchemy import event, func

from .context import normalize_text
import re


_INSTALLED = False


def _history_for_transaction(
    session: Session,
    transaction: Any,
) -> list[dict[str, Any]]:
    model = type(transaction)

    merchant = normalize_text(transaction.merchant_name)

    if not merchant:
        return []

    query = session.query(model)

    # Only retrieve transactions belonging to the same merchant.
    # The categorizer uses normalized merchant names when matching history.
    dialect = session.get_bind().dialect.name

    if dialect == "postgresql":
        # Normalize repeated whitespace in PostgreSQL, matching Python's
        # whitespace normalization for ordinary transaction merchant names.
        query = query.filter(
            func.regexp_replace(
                func.lower(model.merchant_name),
                r"\s+",
                " ",
                "g",
            ) == merchant
        )
    else:
        # SQLite-compatible candidate search. The existing Python filter below
        # performs the final exact normalized-name comparison.
        tokens = [
            token.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            for token in merchant.split()
        ]
        pattern = "%" + "%".join(tokens) + "%"

        query = query.filter(
            func.lower(model.merchant_name).like(pattern, escape="\\")
        )

    transaction_id = getattr(transaction, "id", None)
    if transaction_id is not None:
        query = query.filter(model.id != transaction_id)

    user_id = getattr(transaction, "user_id", None)
    if hasattr(model, "user_id"):
        if user_id is None:
            query = query.filter(model.user_id.is_(None))
        else:
            query = query.filter(model.user_id == user_id)

    with session.no_autoflush:
        rows = query.all()

    return [
        {
            "merchant_name": row.merchant_name,
            "amount": row.amount,
            "category": row.category,
            "note": row.notes,
            "payment_method": row.payment_method,
        }
        for row in rows
        if normalize_text(row.merchant_name) == merchant
    ]
def _resolve_persisted_category(result: dict[str, Any]) -> str:
    if result.get("status") == "categorized" and result.get("category"):
        return str(result["category"])
    return "Unknown"


def _before_flush(
    session: Session,
    flush_context: Any,
    instances: Any,
) -> None:
    candidates = list(session.new) + [obj for obj in session.dirty if obj not in session.new]

    for transaction in candidates:
        if getattr(transaction, "_preserve_category_during_flush", False):
            transaction._preserve_category_during_flush = False
            continue
        if transaction.__class__.__name__ != "Transaction":
            continue
        if not all(
            hasattr(transaction, attribute)
            for attribute in ("merchant_name", "amount", "notes", "payment_method", "category")
        ):
            continue

        history = _history_for_transaction(session, transaction)
        result = categorize_transaction(
            merchant_name=transaction.merchant_name,
            amount=transaction.amount,
            note=transaction.notes,
            payment_method=transaction.payment_method,
            history=history,
        )
        transaction.category = _resolve_persisted_category(result)


def install() -> None:
    """Install the categorization hook once for all SQLAlchemy sessions."""
    global _INSTALLED
    if _INSTALLED:
        return

    event.listen(Session, "before_flush", _before_flush)
    _INSTALLED = True
