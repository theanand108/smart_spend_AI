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

    change = next(item for item in insights if item["insight_type"] == "spending_increase")
    assert change["severity"] == "attention"
    assert change["category"] == "Food & Dining"
    assert change["merchant"] == "Food App"
    assert change["driver"] == "category_and_merchant"
    assert change["recommendation"] == "review_category"
    assert len(change["evidence"]) == 3


def test_category_spike_is_prioritized_as_a_discovery():
    previous = [
        tx(1000, "Food App", "Food & Dining"),
        tx(1000, "Amazon", "Shopping"),
    ]
    current = [
        tx(1800, "Food App", "Food & Dining"),
        tx(1000, "Amazon", "Shopping"),
    ]

    facts = build_financial_facts(current, previous)
    insights = generate_financial_insights(facts)

    assert insights[0]["insight_type"] == "category_spike"
    assert insights[0]["category"] == "Food & Dining"
    assert insights[0]["recommendation"] == "review_category_spike"


def test_category_spike_suppresses_redundant_new_area_and_change_insights():
    previous = [
        tx(1000, "Amazon", "Shopping"),
    ]
    current = [
        tx(1800, "Amazon", "Shopping"),
        tx(948, "Show", "Entertainment"),
    ]

    facts = build_financial_facts(current, previous)
    insights = generate_financial_insights(facts)
    types = [item["insight_type"] for item in insights]

    assert types[0] == "category_spike"
    assert "new_spending_area" not in types
    assert "spending_increase" not in types
    assert len(insights) == len(set((item["insight_type"], item["category"], item["merchant"]) for item in insights))


def test_frequency_change_is_detected_even_when_total_spending_decreases():
    previous = [
        tx(800, "Cafe", "Food & Dining"),
        tx(700, "Cafe", "Food & Dining"),
    ]
    current = [
        tx(400, "Cafe", "Food & Dining"),
        tx(400, "Cafe", "Food & Dining"),
        tx(400, "Cafe", "Food & Dining"),
        tx(400, "Cafe", "Food & Dining"),
    ]

    facts = build_financial_facts(current, previous)
    insights = generate_financial_insights(facts)

    frequency = next(item for item in insights if item["insight_type"] == "frequency_increase")
    assert frequency["driver"] == "frequency_increase"
    assert frequency["recommendation"] == "review_purchase_frequency"


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
    assert frequency["recommendation"] == "review_purchase_frequency"


def test_spending_decrease_gets_positive_maintenance_recommendation():
    previous = [tx(1200, "Food App", "Food & Dining")]
    current = [tx(600, "Food App", "Food & Dining")]

    facts = build_financial_facts(current, previous)
    insights = generate_financial_insights(facts)

    decrease = next(item for item in insights if item["insight_type"] == "spending_decrease")
    assert decrease["severity"] == "positive"
    assert decrease["recommendation"] == "maintain_pattern"


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
