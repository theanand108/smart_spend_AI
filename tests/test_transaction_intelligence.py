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
    history = [{"merchant_name": "RAHUL KUMAR", "category": "Food & Dining", "amount": 60}]
    result = categorize_transaction("RAHUL KUMAR", 55, "", "UPI", history)
    assert result["category"] == "Food & Dining"
    assert result["status"] == "categorized"


def test_stable_personal_history_can_categorize_without_note():
    history = [
        {"merchant_name": "RAHUL KUMAR", "category": "Transfer / Personal", "amount": 500},
        {"merchant_name": "RAHUL KUMAR", "category": "Transfer / Personal", "amount": 700},
        {"merchant_name": "RAHUL KUMAR", "category": "Transfer / Personal", "amount": 1000},
        {"merchant_name": "RAHUL KUMAR", "category": "Transfer / Personal", "amount": 500},
        {"merchant_name": "RAHUL KUMAR", "category": "Food & Dining", "amount": 120},
    ]
    result = categorize_transaction("RAHUL KUMAR", 500, None, "UPI", history)
    assert result["category"] == "Transfer / Personal"
    assert result["status"] == "categorized"
    assert result["needs_user_confirmation"] is False
    assert result["personal_category_candidate"] == "Transfer / Personal"


def test_varies_personal_history_does_not_force_no_note_transaction():
    history = [
        {"merchant_name": "RAHUL KUMAR", "category": "Food & Dining", "amount": 300},
        {"merchant_name": "RAHUL KUMAR", "category": "Groceries", "amount": 500},
        {"merchant_name": "RAHUL KUMAR", "category": "Health & Fitness", "amount": 650},
        {"merchant_name": "RAHUL KUMAR", "category": "Transfer / Personal", "amount": 1000},
    ]
    result = categorize_transaction("RAHUL KUMAR", 500, None, "UPI", history)
    assert result["category"] is None
    assert result["status"] == "varies"
    assert result["needs_user_confirmation"] is True


def test_repeated_amount_can_break_a_tied_history():
    history = [
        {"merchant_name": "RAHUL KUMAR", "category": "Food & Dining", "amount": 500},
        {"merchant_name": "RAHUL KUMAR", "category": "Food & Dining", "amount": 500},
        {"merchant_name": "RAHUL KUMAR", "category": "Groceries", "amount": 2000},
        {"merchant_name": "RAHUL KUMAR", "category": "Groceries", "amount": 2100},
    ]
    result = categorize_transaction("RAHUL KUMAR", 500, None, "UPI", history)
    assert result["category"] == "Food & Dining"
    assert result["status"] == "categorized"
    assert result["needs_user_confirmation"] is False


def test_unseen_amount_does_not_break_tied_history():
    history = [
        {"merchant_name": "RAHUL KUMAR", "category": "Food & Dining", "amount": 500},
        {"merchant_name": "RAHUL KUMAR", "category": "Groceries", "amount": 2000},
    ]
    result = categorize_transaction("RAHUL KUMAR", 900, None, "UPI", history)
    assert result["category"] is None
    assert result["status"] == "conflict"
    assert result["needs_user_confirmation"] is True


def test_small_history_without_amount_match_stays_unresolved():
    history = [
        {"merchant_name": "MOHAN", "category": "Transfer / Personal", "amount": 500},
        {"merchant_name": "MOHAN", "category": "Transfer / Personal", "amount": 500},
    ]
    result = categorize_transaction("MOHAN", 3000, None, "UPI", history)
    assert result["category"] is None
    assert result["status"] == "unknown"
    assert result["needs_user_confirmation"] is True


def test_repeated_historical_semantics_can_support_varies_entity():
    history = [
        {"merchant_name": "ANITA DEVI", "category": "Health & Fitness", "amount": 850, "note": "Medicines"},
        {"merchant_name": "ANITA DEVI", "category": "Health & Fitness", "amount": 600, "note": "Pharmacy"},
        {"merchant_name": "ANITA DEVI", "category": "Shopping", "amount": 1200, "note": "Clothes"},
        {"merchant_name": "ANITA DEVI", "category": "Education", "amount": 5000, "note": "College fee"},
    ]
    result = categorize_transaction("ANITA DEVI", 850, None, "UPI", history)
    assert result["category"] == "Health & Fitness"
    assert result["status"] == "needs_confirmation"
    assert result["needs_user_confirmation"] is True


def test_conflicting_history_requires_confirmation():
    history = [
        {"merchant_name": "RAHUL KUMAR", "category": "Food & Dining"},
        {"merchant_name": "RAHUL KUMAR", "category": "Housing / Rent"},
    ]
    result = categorize_transaction("RAHUL KUMAR", 5000, "", "UPI", history)
    assert result["category"] is None
    assert result["status"] == "conflict"
    assert result["needs_user_confirmation"] is True


def test_strong_current_note_overrides_conflicting_history():
    history = [
        {"merchant_name": "RAHUL KUMAR", "category": "Food & Dining"},
        {"merchant_name": "RAHUL KUMAR", "category": "Housing / Rent"},
    ]
    result = categorize_transaction("RAHUL KUMAR", 5000, "Monthly room rent", "UPI", history)
    assert result["category"] == "Housing / Rent"
    assert result["status"] == "categorized"
    assert result["needs_user_confirmation"] is False


def test_ambiguous_gift_note_stays_unknown_without_context():
    result = categorize_transaction("ANITA DEVI", 1999, "gift", "UPI")
    assert result["category"] is None
    assert result["status"] == "unknown"
    assert result["needs_user_confirmation"] is True


def test_amazon_books_note_overrides_generic_amazon_shopping_mapping():
    result = categorize_transaction("Amazon", 650, "for books", "UPI")
    assert result["category"] == "Education"
    assert result["status"] == "categorized"
    assert result["needs_user_confirmation"] is False


def test_qualified_amazon_groceries_merchant_overrides_generic_amazon_mapping():
    result = categorize_transaction("Amazon Pay Groceries", 1200, None, "UPI")
    assert result["category"] == "Groceries"
    assert result["status"] == "categorized"
    assert result["needs_user_confirmation"] is False


def test_personal_self_note_is_transfer_personal():
    result = categorize_transaction("Anand bank", 5000, "personal self", "UPI")
    assert result["category"] == "Transfer / Personal"
    assert result["status"] == "categorized"
    assert result["needs_user_confirmation"] is False


def test_simple_personal_transfer_notes_are_transfer_personal():
    notes = [
        "self",
        "personal",
        "self transaction",
        "personal transaction",
        "self transfer",
        "personal transfer",
        "transfer to self",
        "transfer to my account",
        "own account",
    ]
    for note in notes:
        result = categorize_transaction("Anand bank", 5000, note, "UPI")
        assert result["category"] == "Transfer / Personal", note
        assert result["status"] == "categorized", note
        assert result["needs_user_confirmation"] is False, note


def test_personal_word_inside_longer_purchase_note_is_not_a_personal_transfer():
    result = categorize_transaction("Amazon", 1500, "personal shopping for clothes", "UPI")
    assert result["category"] != "Transfer / Personal"


def test_strong_merchant_and_note_disagreement_is_conflict():
    result = categorize_transaction("Book shop", 1000, "purchased an electronics", "UPI")
    assert result["category"] is None
    assert result["status"] == "conflict"
    assert result["needs_user_confirmation"] is True
    assert set(result["conflicting_categories"]) == {"Education", "Shopping"}


def test_strong_merchant_note_agreement_still_categorizes():
    result = categorize_transaction("Book shop", 1000, "purchased some books", "UPI")
    assert result["category"] == "Education"
    assert result["status"] == "categorized"
    assert result["needs_user_confirmation"] is False
