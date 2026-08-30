"""Build a small, presentation-neutral queue of transactions needing attention."""

from __future__ import annotations

from typing import Any, Iterable

from .categorizer import categorize_transaction


ATTENTION_STATUSES = {"conflict", "unknown", "varies"}
STATUS_PRIORITY = {"conflict": 0, "varies": 1, "unknown": 2}


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

    This function deliberately does not mutate transactions. The dashboard can
    use it to surface conflicts and unknowns while leaving normal categorized
    transactions completely out of the attention queue.
    """
    transaction_list = list(transactions)
    history = _history_rows(transaction_list)
    attention: list[dict[str, Any]] = []

    for transaction in transaction_list:
        result = categorize_transaction(
            getattr(transaction, "merchant_name", ""),
            getattr(transaction, "amount", None),
            getattr(transaction, "notes", None),
            getattr(transaction, "payment_method", None),
            history,
        )
        status = result.get("status")
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
