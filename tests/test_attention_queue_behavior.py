from datetime import datetime
from types import SimpleNamespace

from src.intelligence.attention import build_attention_queue
from src.intelligence.categorizer import categorize_transaction


def transaction(merchant, amount, category="Unknown", notes=None):
    return SimpleNamespace(
        id=1,
        merchant_name=merchant,
        amount=amount,
        category=category,
        notes=notes,
        payment_method="UPI",
        date=datetime(2026, 8, 30),
    )


def test_resolved_transaction_does_not_return_to_attention_queue():
    resolved = transaction("Himanshu", 700, category="Groceries")

    assert build_attention_queue([resolved]) == []


def test_vague_note_does_not_hide_a_real_history_conflict():
    history = [
        {"merchant_name": "Conflict Test Merchant", "amount": 500, "category": "Food & Dining", "note": None},
        {"merchant_name": "Conflict Test Merchant", "amount": 700, "category": "Food & Dining", "note": None},
        {"merchant_name": "Conflict Test Merchant", "amount": 600, "category": "Shopping", "note": None},
        {"merchant_name": "Conflict Test Merchant", "amount": 800, "category": "Shopping", "note": None},
    ]

    result = categorize_transaction(
        "Conflict Test Merchant",
        650,
        "payment",
        "UPI",
        history,
    )

    assert result["status"] == "conflict"
    assert result["category"] is None
