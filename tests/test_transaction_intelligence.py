from src.intelligence.categorizer import categorize_transaction


def test_known_merchant_preserves_v1_behavior():
    result = categorize_transaction("ZOMATO", 420, None, "UPI")
    assert result["category"] == "Food & Dining"
    assert result["status"] == "categorized"
    assert result["needs_user_confirmation"] is False


def test_personal_name_without_context_is_unknown():
    result = categorize_transaction("RAHUL KUMAR", 350, None, "UPI")
    assert result["category"] is None
    assert result["status"] == "unknown"
    assert result["needs_user_confirmation"] is True


def test_note_adds_context_to_personal_name():
    result = categorize_transaction("RAHUL KUMAR", 350, "Tea from college shop", "UPI")
    assert result["category"] == "Food & Dining"
    assert result["status"] == "categorized"
    assert result["confidence"] >= 0.8


def test_weak_note_does_not_create_false_confidence():
    result = categorize_transaction("ANITA DEVI", 850, "ok", "UPI")
    assert result["category"] is None
    assert result["status"] == "unknown"
    assert result["needs_user_confirmation"] is True


def test_history_can_resolve_repeated_personal_merchant():
    history = [
        {
            "merchant_name": "RAHUL KUMAR",
            "category": "Food & Dining",
            "amount": 60,
        }
    ]
    result = categorize_transaction("RAHUL KUMAR", 55, "", "UPI", history)
    assert result["category"] == "Food & Dining"
    assert result["status"] == "categorized"


def test_conflicting_history_requires_confirmation():
    history = [
        {"merchant_name": "RAHUL KUMAR", "category": "Food & Dining"},
        {"merchant_name": "RAHUL KUMAR", "category": "Housing / Rent"},
    ]
    result = categorize_transaction("RAHUL KUMAR", 5000, "", "UPI", history)
    assert result["category"] is None
    assert result["status"] == "conflict"
    assert result["needs_user_confirmation"] is True


def test_current_context_can_flag_historical_conflict():
    history = [
        {"merchant_name": "RAHUL KUMAR", "category": "Food & Dining"},
    ]
    result = categorize_transaction("RAHUL KUMAR", 5000, "Monthly room rent", "UPI", history)
    assert result["category"] == "Housing / Rent"
    assert result["status"] == "conflict"
    assert result["needs_user_confirmation"] is True


def test_ambiguous_gift_note_stays_unknown_without_context():
    result = categorize_transaction("ANITA DEVI", 1999, "gift", "UPI")
    assert result["category"] is None
    assert result["status"] == "unknown"
    assert result["needs_user_confirmation"] is True
