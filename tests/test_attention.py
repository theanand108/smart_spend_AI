from datetime import datetime

from src.intelligence.attention import build_attention_queue, summarize_attention_queue


class FakeTransaction:
    def __init__(self, merchant_name, amount, category=None, notes=None, payment_method="UPI"):
        self.id = None
        self.date = datetime(2026, 8, 30)
        self.merchant_name = merchant_name
        self.amount = amount
        self.category = category
        self.notes = notes
        self.payment_method = payment_method


def test_attention_queue_excludes_confident_transactions():
    transactions = [
        FakeTransaction("DEEPAK FRUIT CENTRE", 200, "Groceries"),
        FakeTransaction("EKART", 673, "Unknown"),
    ]

    attention = build_attention_queue(transactions)

    assert len(attention) == 1
    assert attention[0]["transaction"].merchant_name == "EKART"
    assert attention[0]["status"] == "unknown"


def test_attention_queue_prioritizes_conflicts_over_unknowns():
    transactions = [
        FakeTransaction("ANITA DEVI", 900, "Unknown"),
        FakeTransaction("RAHUL KUMAR", 5000, "Unknown"),
    ]

    # Give Rahul contradictory historical categories through separate rows.
    transactions.extend(
        [
            FakeTransaction("RAHUL KUMAR", 300, "Food & Dining"),
            FakeTransaction("RAHUL KUMAR", 400, "Housing / Rent"),
        ]
    )

    attention = build_attention_queue(transactions)

    assert attention
    assert attention[0]["status"] == "conflict"


def test_attention_summary_counts_statuses():
    attention = [
        {"status": "conflict"},
        {"status": "unknown"},
        {"status": "unknown"},
        {"status": "varies"},
    ]

    assert summarize_attention_queue(attention) == {
        "total": 4,
        "conflicts": 1,
        "unknown": 2,
        "varies": 1,
    }


def test_attention_queue_excludes_explicit_transfer_personal_correction():
    transactions = [
        FakeTransaction("ANAND BANK", 1000, "Transfer / Personal", "payment"),
    ]

    assert build_attention_queue(transactions) == []


def test_attention_queue_excludes_explicit_personal_care_category():
    transactions = [
        FakeTransaction("sajir", 350, "Personal Care", "paid to sajir barber"),
    ]

    assert build_attention_queue(transactions) == []
