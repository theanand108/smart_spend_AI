from src.intelligence.categorizer import categorize_transaction
from src.intelligence.evidence import collect_evidence


def test_entity_history_is_real_evidence_for_future_transaction():
    history = [
        {"merchant_name": "RAHUL KUMAR", "category": "Food & Dining", "amount": 400, "note": "dinner"},
        {"merchant_name": "RAHUL KUMAR", "category": "Food & Dining", "amount": 450, "note": "lunch"},
        {"merchant_name": "RAHUL KUMAR", "category": "Food & Dining", "amount": 420, "note": "food"},
        {"merchant_name": "RAHUL KUMAR", "category": "Food & Dining", "amount": 430, "note": "restaurant"},
    ]
    result = categorize_transaction("RAHUL KUMAR", 425, "payment", "UPI", history)

    assert result["category"] == "Food & Dining"
    assert result["status"] == "needs_confirmation"
    assert result["needs_user_confirmation"] is True
    assert result["entity_memory"]["memory_label"] == "STABLE"


def test_unknown_history_is_not_counted_as_learning_signal():
    history = [
        {"merchant_name": "RAHUL KUMAR", "category": "Unknown", "amount": 500, "note": "payment"},
    ]
    evidence = collect_evidence(
        amount=500,
        note="payment",
        merchant_name="RAHUL KUMAR",
        payment_method="UPI",
        history=history,
    )

    assert all(category != "Unknown" for category, _score in evidence["ranked"])


def test_strong_note_can_outweigh_entity_history():
    history = [
        {"merchant_name": "RAHUL KUMAR", "category": "Food & Dining", "amount": 400, "note": "dinner"},
        {"merchant_name": "RAHUL KUMAR", "category": "Shopping", "amount": 1200, "note": "shopping"},
        {"merchant_name": "RAHUL KUMAR", "category": "Housing / Rent", "amount": 8000, "note": "monthly rent"},
    ]
    result = categorize_transaction("RAHUL KUMAR", 2500, "monthly room rent", "UPI", history)

    assert result["category"] == "Housing / Rent"
    assert result["status"] == "categorized"
