"""Build a small, presentation-neutral queue of transactions needing attention."""

from __future__ import annotations

from typing import Any, Iterable

from .categorizer import categorize_transaction


ATTENTION_STATUSES = {"conflict", "unknown", "varies"}
STATUS_PRIORITY = {"conflict": 0, "varies": 1, "unknown": 2}
RESOLVED_CATEGORIES = {"Food & Dining", "Travel & Transport", "Entertainment", "Groceries", "Bills & Utilities", "Shopping", "Health & Fitness", "Transfer / Personal", "Others"}


def _history_rows(transactions: Iterable[Any]) -> list[dict[str, Any]]:
    """Convert transaction-like objects into the categorizer's history shape."""
    rows: list[dict[str, Any]] = []
    for transaction in transactions:
        rows.append(
            {
                "merchant_name": getattr(transaction, "merchant_name", None),
                "category": getattr(transaction, "category", None),
                "amount": getattr(transaction, "amount", None),
                "note": getattr(transaction, "notes", None),
            }
        )
    return rows


def build_attention_queue(transactions: Iterable[Any]) -> list[dict[str, Any]]:
    """Evaluate transactions and return only unresolved intelligence states.

    Explicitly categorized transactions have already been resolved by the user
    or by the persistence layer and must not re-enter the attention queue merely
    because re-evaluating them without their own row produces an unknown state.

    Stored ``Unknown`` transactions are different: they represent an unresolved
    decision and must remain reviewable even if a later intelligence pass can
    now produce a category suggestion from the surrounding history. In that
    case the suggestion is shown as supporting evidence, while the transaction
    remains in the queue until the user explicitly resolves it.
    """
    transaction_list = list(transactions)
    history = _history_rows(transaction_list)
    attention: list[dict[str, Any]] = []

    for transaction in transaction_list:
        stored_category = getattr(transaction, "category", None)
        if stored_category in RESOLVED_CATEGORIES:
            continue

        result = categorize_transaction(
            getattr(transaction, "merchant_name", ""),
            getattr(transaction, "amount", None),
            getattr(transaction, "notes", None),
            getattr(transaction, "payment_method", None),
            history,
        )
        status = result.get("status")

        # An explicitly stored Unknown is still unresolved. Never let a later
        # re-evaluation silently remove it from the user's review queue.
        if stored_category == "Unknown" and status not in ATTENTION_STATUSES:
            status = "unknown"

        if status not in ATTENTION_STATUSES:
            continue

        attention.append(
            {
                "transaction": transaction,
                "status": status,
                "category": result.get("category"),
                "confidence": result.get("confidence", 0.0),
                "reason": result.get("reason", ""),
                "needs_user_confirmation": result.get("needs_user_confirmation", True),
            }
        )

    attention.sort(
        key=lambda item: (
            STATUS_PRIORITY.get(item["status"], 99),
            -float(item.get("confidence") or 0.0),
            getattr(item["transaction"], "date", None) or 0,
        )
    )
    return attention


def summarize_attention_queue(attention: list[dict[str, Any]]) -> dict[str, int]:
    """Return stable counts for dashboard summaries."""
    return {
        "total": len(attention),
        "conflicts": sum(item["status"] == "conflict" for item in attention),
        "unknown": sum(item["status"] == "unknown" for item in attention),
        "varies": sum(item["status"] == "varies" for item in attention),
    }
