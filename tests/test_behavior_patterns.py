from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

from src.analytics.behavior_patterns import detect_behavior_patterns
from src.analytics.financial_facts import build_financial_facts


def tx(amount, merchant, category, day=1):
    return SimpleNamespace(
        amount=amount,
        merchant_name=merchant,
        category=category,
        date=datetime(2026, 8, day),
    )


def patterns(current, previous):
    facts = build_financial_facts(current, previous)
    return detect_behavior_patterns(facts)


def test_detects_frequency_driven_increase_when_average_stays_stable():
    previous = [tx(500, "Cafe", "Food & Dining")]
    current = [tx(500, "Cafe", "Food & Dining")] * 3
    result = patterns(current, previous)
    frequency = next(item for item in result if item["pattern_type"] == "frequency_driven_increase")
    assert frequency["confidence"] >= Decimal("0.80")
    assert "Transaction count increased by 2." in frequency["evidence"]


def test_does_not_call_a_larger_basket_a_frequency_pattern():
    previous = [tx(600, "Store", "Shopping"), tx(600, "Store", "Shopping")]
    current = [tx(1200, "Store", "Shopping"), tx(1200, "Store", "Shopping")]
    result = patterns(current, previous)
    assert any(item["pattern_type"] == "basket_size_driven_increase" for item in result)
    assert not any(item["pattern_type"] == "frequency_driven_increase" for item in result)


def test_detects_new_spending_area():
    previous = [tx(1000, "Cafe", "Food & Dining")]
    current = [tx(1000, "Cafe", "Food & Dining"), tx(800, "Bookstore", "Education")]
    result = patterns(current, previous)
    new_area = next(item for item in result if item["pattern_type"] == "new_spending_area")
    assert new_area["category"] == "Education"
    assert new_area["merchant"] is None


def test_detects_merchant_driven_increase_when_one_merchant_dominates():
    previous = [tx(500, "Cafe", "Food & Dining")]
    current = [tx(1200, "Cafe", "Food & Dining"), tx(300, "Store", "Shopping")]
    result = patterns(current, previous)
    merchant = next(item for item in result if item["pattern_type"] == "merchant_driven_increase")
    assert merchant["merchant"] == "Cafe"
    assert merchant["confidence"] > 0.90


def test_detects_distributed_increase_without_naming_a_single_category():
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
    result = patterns(current, previous)
    distributed = next(item for item in result if item["pattern_type"] == "distributed_increase")
    assert distributed["category"] is None
    assert distributed["merchant"] is None
    assert "3 categories increased spending." in distributed["evidence"]


def test_small_new_category_is_not_treated_as_a_new_spending_area():
    previous = [tx(1000, "Cafe", "Food & Dining")]
    current = [tx(1000, "Cafe", "Food & Dining"), tx(100, "Bookstore", "Education")]
    result = patterns(current, previous)
    assert not any(item["pattern_type"] == "new_spending_area" for item in result)
