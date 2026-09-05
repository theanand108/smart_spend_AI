from src.intelligence.entity_memory import build_entity_profile, should_create_personal_category


def tx(category, amount=500):
    return {"merchant_name": "Rahul", "category": category, "amount": amount}


def test_person_with_mixed_purposes_is_varies():
    history = [
        tx("Food & Dining"),
        tx("Groceries"),
        tx("Health & Fitness"),
        tx("Transfer / Personal"),
    ]
    profile = build_entity_profile("Rahul", history)
    assert profile["memory_label"] == "VARIES"
    assert profile["dominant_category"] is None
    assert not should_create_personal_category(profile)


def test_stable_personal_purpose_can_become_personal_category_candidate():
    history = [
        tx("Transfer / Personal"),
        tx("Transfer / Personal"),
        tx("Transfer / Personal"),
        tx("Transfer / Personal"),
        tx("Food & Dining"),
    ]
    profile = build_entity_profile("Rahul", history)
    assert profile["memory_label"] == "STABLE"
    assert profile["dominant_category"] == "Transfer / Personal"
    assert should_create_personal_category(profile)


def test_small_history_does_not_create_personal_category():
    profile = build_entity_profile(
        "Rahul",
        [tx("Transfer / Personal"), tx("Transfer / Personal")],
    )
    assert profile["memory_label"] == "STABLE"
    assert not should_create_personal_category(profile)


def test_unknown_history_is_not_treated_as_a_category():
    profile = build_entity_profile(
        "Rahul",
        [tx("Unknown"), tx("Others"), tx(None)],
    )
    assert profile["category_counts"] == {}
    assert profile["memory_label"] == "UNKNOWN"
