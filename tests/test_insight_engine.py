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


def test_generates_change_driver_and_actionable_recommendation():
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
    insights = generate_financial_insights(facts)

    assert insights
    insight = insights[0]
    assert insight["insight_type"] == "spending_increase"
    assert insight["severity"] == "attention"
    assert insight["category"] == "Food & Dining"
    assert insight["merchant"] == "Food App"
    assert insight["driver"] == "category_and_merchant"
    assert insight["recommendation"] == "review_category"
    assert len(insight["evidence"]) == 3


def test_frequency_pattern_is_distinguished_from_larger_transactions():
    previous = [tx(500, "Cafe", "Food & Dining")]
    current = [
        tx(500, "Cafe", "Food & Dining"),
        tx(500, "Cafe", "Food & Dining"),
        tx(500, "Cafe", "Food & Dining"),
    ]

    facts = build_financial_facts(current, previous)
    insights = generate_financial_insights(facts)

    frequency = next(item for item in insights if item["insight_type"] == "frequency_increase")
    assert frequency["driver"] == "frequency_increase"
    assert frequency["recommendation"] == "reduce_frequency"


def test_spending_decrease_gets_positive_maintenance_recommendation():
    previous = [tx(1200, "Food App", "Food & Dining")]
    current = [tx(600, "Food App", "Food & Dining")]

    facts = build_financial_facts(current, previous)
    insights = generate_financial_insights(facts)

    assert insights[0]["insight_type"] == "spending_decrease"
    assert insights[0]["severity"] == "positive"
    assert insights[0]["recommendation"] == "maintain_pattern"


def test_small_change_does_not_create_noise():
    previous = [tx(1000, "Cafe", "Food & Dining")]
    current = [tx(1050, "Cafe", "Food & Dining")]

    facts = build_financial_facts(current, previous)

    assert generate_financial_insights(facts) == []


def test_limit_controls_number_of_insights():
    previous = [
        tx(1000, "Cafe", "Food & Dining"),
        tx(500, "Amazon", "Shopping"),
    ]
    current = [
        tx(1200, "Cafe", "Food & Dining"),
        tx(1200, "Cafe", "Food & Dining"),
        tx(500, "Amazon", "Shopping"),
        tx(500, "Amazon", "Shopping"),
    ]

    facts = build_financial_facts(current, previous)

    assert len(generate_financial_insights(facts, limit=1)) == 1
