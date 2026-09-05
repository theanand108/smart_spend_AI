from datetime import datetime

from src.intelligence.attention import build_attention_queue


class FakeTransaction:
    def __init__(self, merchant_name, amount, category=None, notes=None):
        self.id = None
        self.date = datetime(2026, 8, 30)
        self.merchant_name = merchant_name
        self.amount = amount
        self.category = category
        self.notes = notes
        self.payment_method = "UPI"


def test_stored_unknown_remains_reviewable_when_intelligence_has_a_suggestion():
    transactions = [
        FakeTransaction("ZOMATO", 420, "Unknown"),
    ]

    attention = build_attention_queue(transactions)

    assert len(attention) == 1
    assert attention[0]["transaction"].merchant_name == "ZOMATO"
    assert attention[0]["status"] == "unknown"
    assert attention[0]["category"] == "Food & Dining"
