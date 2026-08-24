from src.intelligence.semantic import semantic_note_evidence


def test_learned_model_handles_unseen_health_phrase():
    result = semantic_note_evidence("prescription refill from the chemist")
    assert result["category"] == "Health & Fitness"
    assert result["confidence"] >= 0.72


def test_learned_model_handles_unseen_entertainment_phrase():
    result = semantic_note_evidence("bought a ticket for the cinema")
    assert result["category"] == "Entertainment"
    assert result["confidence"] >= 0.72


def test_learned_model_can_abstain_on_weak_language():
    result = semantic_note_evidence("no details")
    assert result["category"] is None
