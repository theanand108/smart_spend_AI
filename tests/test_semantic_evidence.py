from src.intelligence.semantic import semantic_note_evidence


def test_medicine_note_is_strong_health_evidence():
    result = semantic_note_evidence("bought medicine for mom")
    assert result["category"] == "Health & Fitness"
    assert result["confidence"] >= 0.9


def test_friend_dinner_share_is_personal_transfer():
    result = semantic_note_evidence("sent my share of dinner to Rahul")
    assert result["category"] == "Transfer / Personal"
    assert result["confidence"] >= 0.78


def test_vegetables_for_us_is_groceries():
    result = semantic_note_evidence("Rahul got vegetables for us")
    assert result["category"] == "Groceries"


def test_vague_note_has_no_semantic_category():
    result = semantic_note_evidence("got something")
    assert result["candidates"] == []
    assert result["confidence"] == 0.0


def test_conflicting_note_does_not_pick_a_winner():
    result = semantic_note_evidence("bought medicine and dinner")
    assert result["category"] is None
    assert result["confidence"] == 0.0
