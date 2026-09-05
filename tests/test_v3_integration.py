from src.intelligence.categorizer import categorize_transaction
from src.intelligence.semantic_ml import learned_semantic_evidence


def test_v3_learned_semantics_accepts_targeted_unseen_health_phrase():
    result = learned_semantic_evidence("had a blood test at the clinic")
    assert result["category"] == "Health & Fitness"
    assert result["confidence"] >= 0.35
    assert result["margin"] >= 0.10


def test_v3_learned_semantics_still_abstains_on_vague_note():
    result = learned_semantic_evidence("no details")
    assert result["category"] is None


def test_v3_semantic_note_overrides_mixed_entity_history():
    history = [
        {"merchant_name": "RAHUL KUMAR", "category": "Food & Dining", "amount": 400},
        {"merchant_name": "RAHUL KUMAR", "category": "Shopping", "amount": 1200},
        {"merchant_name": "RAHUL KUMAR", "category": "Housing / Rent", "amount": 8000},
    ]
    result = categorize_transaction(
        "RAHUL KUMAR",
        2500,
        "monthly room rent",
        "UPI",
        history,
    )
    assert result["category"] == "Housing / Rent"
    assert result["status"] == "categorized"
    assert result["needs_user_confirmation"] is False


def test_v3_strong_cross_source_disagreement_remains_a_conflict():
    result = categorize_transaction(
        "Book shop",
        1000,
        "purchased an electronics",
        "UPI",
    )
    assert result["category"] is None
    assert result["status"] == "conflict"
    assert result["needs_user_confirmation"] is True
    assert set(result["conflicting_categories"]) == {"Education", "Shopping"}
