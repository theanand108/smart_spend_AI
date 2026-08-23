from src.intelligence.semantic import semantic_note_evidence


def test_medicine_note_is_strong_health_evidence():
    result = semantic_note_evidence("bought medicine for mom")
    assert result["category"] == "Health & Fitness"
    assert result["confidence"] >= 0.9


def test_friend_dinner_share_is_food_not_personal_transfer():
    result = semantic_note_evidence("sent my share of dinner to Rahul")
    assert result["category"] == "Food & Dining"
    assert result["confidence"] >= 0.9


def test_friend_medicine_payment_is_health_not_personal_transfer():
    result = semantic_note_evidence("sent Rahul money for medicine")
    assert result["category"] == "Health & Fitness"


def test_lending_money_to_friend_is_personal_transfer():
    result = semantic_note_evidence("lent money to Rahul")
    assert result["category"] == "Transfer / Personal"


def test_allowance_is_personal_transfer():
    result = semantic_note_evidence("monthly allowance")
    assert result["category"] == "Transfer / Personal"


def test_reimbursement_is_personal_transfer():
    result = semantic_note_evidence("refund for shared purchase")
    assert result["category"] == "Transfer / Personal"


def test_weak_personal_note_is_not_a_category():
    result = semantic_note_evidence("personal")
    assert result["category"] is None
    assert result["confidence"] == 0.0


def test_weak_home_note_is_not_a_category():
    result = semantic_note_evidence("home")
    assert result["category"] is None
    assert result["confidence"] == 0.0


def test_vegetables_for_us_is_groceries():
    result = semantic_note_evidence("Rahul got vegetables for us")
    assert result["category"] == "Groceries"


def test_vague_note_has_no_semantic_category():
    result = semantic_note_evidence("got something")
    assert result["candidates"] == []
    assert result["confidence"] == 0.0
    assert result["category"] is None


def test_conflicting_note_does_not_pick_a_winner():
    result = semantic_note_evidence("bought medicine and dinner")
    assert result["category"] is None
    assert result["confidence"] == 0.0
