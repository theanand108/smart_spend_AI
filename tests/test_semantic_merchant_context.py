from src.intelligence.semantic import semantic_note_evidence


def test_common_merchant_context_is_groceries():
    cases = [
        "Gupta General Store",
        "ARMAN Kirana",
        "DEEPAK FRUIT CENTRE",
    ]

    for text in cases:
        result = semantic_note_evidence(text)
        assert result["category"] == "Groceries"
        assert result["candidates"] == [("Groceries", 1)]


def test_delivery_merchant_without_purchase_context_abstains():
    result = semantic_note_evidence("EKART")

    assert result["category"] is None
    assert result["candidates"] == []
