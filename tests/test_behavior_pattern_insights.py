from datetime import datetime
from types import SimpleNamespace

from src.analytics.financial_facts import build_financial_facts
from src.analytics.insight_engine import generate_financial_insights


def tx(amount, merchant, category, day=1):
    return SimpleNamespace(
        amount=amount,
        merchant_name=merchant,
        category=category,
        date=datetime(2026, 8, day),
    )


def insights(current, previous):
    facts = build_financial_facts(current, previous)
    return generate_financial_insights(facts, limit=10)


def test_new_spending_area_becomes_an_actionable_insight():
    previous = [tx(1000, "Cafe", "Food & Dining")]
    current = [tx(1000, "Cafe", "Food & Dining"), tx(800, "Bookstore", "Education")]
    result = insights(current, previous)
    insight = next(item for item in result if item["insight_type"] == "new_spending_area")
    assert insight["category"] == "Education"
    assert insight["recommendation"] == "review_new_category"
    assert insight["severity"] == "observation"


def test_basket_size_pattern_becomes_an_actionable_insight():
    previous = [tx(600, "Store", "Shopping"), tx(600, "Store", "Shopping")]
    current = [tx(1200, "Store", "Shopping"), tx(1200, "Store", "Shopping")]
    result = insights(current, previous)
    insight = next(item for item in result if item["insight_type"] == "basket_size_increase")
    assert insight["driver"] == "basket_size_increase"
    assert insight["recommendation"] == "review_large_purchases"


def test_distributed_pattern_does_not_name_a_single_cause():
    previous = [
        tx(1000, "A", "Food & Dining"),
        tx(1000, "B", "Shopping"),
        tx(1000, "C", "Travel & Transport"),
    ]
    current = [
        tx(1300, "A", "Food & Dining"),
        tx(1300, "B", "Shopping"),
        tx(1300, "C", "Travel & Transport"),
    ]
    result = insights(current, previous)
    insight = next(item for item in result if item["insight_type"] == "distributed_increase")
    assert insight["category"] is None
    assert insight["merchant"] is None
    assert insight["recommendation"] == "review_overall_spending"
