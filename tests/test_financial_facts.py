from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

from src.analytics.financial_facts import build_financial_facts


def tx(amount, merchant, category, day=1):
    return SimpleNamespace(
        amount=amount,
        merchant_name=merchant,
        category=category,
        date=datetime(2026, 8, day),
    )


def test_build_financial_facts_explains_monthly_change_and_drivers():
    previous = [
        tx(1000, "Food App", "Food & Dining"),
        tx(500, "Amazon", "Shopping"),
    ]
    current = [
        tx(1200, "Food App", "Food & Dining"),
        tx(800, "Food App", "Food & Dining"),
        tx(500, "Amazon", "Shopping"),
    ]

    facts = build_financial_facts(current, previous)

    assert facts.current_spending == Decimal("2500")
    assert facts.previous_spending == Decimal("1500")
    assert facts.spending_change == Decimal("1000")
    assert facts.spending_change_percent == Decimal("66.66666666666666666666666667")
    assert facts.current_transaction_count == 3
    assert facts.previous_transaction_count == 2
    assert facts.transaction_count_change == 1
    assert facts.current_average_transaction == Decimal("2500") / Decimal("3")
    assert facts.top_current_category == "Food & Dining"
    assert facts.top_current_category_amount == Decimal("2000")

    food = next(item for item in facts.category_changes if item.category == "Food & Dining")
    assert food.amount_change == Decimal("1000")
    assert food.previous_amount == Decimal("1000")

    food_merchant = next(item for item in facts.merchant_changes if item.merchant == "Food App")
    assert food_merchant.amount_change == Decimal("1000")
    assert food_merchant.current_count == 2
    assert food_merchant.previous_count == 1


def test_unknown_and_others_are_not_treated_as_real_categories():
    current = [
        tx(400, "Merchant A", "Unknown"),
        tx(300, "Merchant B", "Others"),
        tx(200, "Merchant C", "Food & Dining"),
    ]

    facts = build_financial_facts(current, [])

    assert facts.current_categories == {"Food & Dining": Decimal("200")}
    assert facts.top_current_category == "Food & Dining"
    assert facts.largest_current_transaction["amount"] == Decimal("400")


def test_zero_previous_period_has_no_fake_percentage_change():
    facts = build_financial_facts([tx(500, "Cafe", "Food & Dining")], [])

    assert facts.spending_change == Decimal("500")
    assert facts.spending_change_percent is None
    assert facts.transaction_count_change_percent is None
    assert facts.average_transaction_change_percent is None
