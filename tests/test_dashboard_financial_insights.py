from datetime import datetime

import pytest

from app import Transaction, app, db


@pytest.fixture
def dashboard_app(tmp_path):
    db_path = tmp_path / "dashboard.db"
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def add_transaction(month, amount, merchant, category, day=1):
    db.session.add(
        Transaction(
            date=datetime(datetime.now().year, month, day),
            merchant_name=merchant,
            amount=amount,
            category=category,
            payment_method="UPI",
        )
    )


def seed_structured_insight_transactions():
    add_transaction(7, 1000, "Food App", "Food & Dining")
    add_transaction(7, 500, "Amazon", "Shopping")
    add_transaction(8, 1200, "Food App", "Food & Dining")
    add_transaction(8, 800, "Food App", "Food & Dining")
    add_transaction(8, 500, "Bookstore", "Education")
    db.session.commit()


def test_dashboard_renders_structured_financial_insights(dashboard_app):
    with dashboard_app.app_context():
        seed_structured_insight_transactions()

    with dashboard_app.test_client() as client:
        response = client.get("/dashboard/8")

    html = response.data.decode("utf-8")
    assert response.status_code == 200
    assert "Financial Insights" in html
    assert "Spending increased" in html
    assert "+₹1,000" in html
    assert "Food &amp; Dining" in html
    assert "Food App" in html


def test_search_filter_does_not_change_financial_insights(dashboard_app):
    with dashboard_app.app_context():
        seed_structured_insight_transactions()

    with dashboard_app.test_client() as client:
        response = client.get("/dashboard/8?q=Bookstore")

    html = response.data.decode("utf-8")
    assert response.status_code == 200
    assert "Bookstore" in html
    assert "Food App" in html
    assert "+₹1,000" in html


def test_dashboard_falls_back_to_key_insights_when_structured_empty(
    dashboard_app, monkeypatch
):
    monkeypatch.setattr("app.generate_financial_insights", lambda facts, limit=3: [])

    with dashboard_app.app_context():
        add_transaction(8, 1500, "Cafe", "Food & Dining")
        add_transaction(8, 600, "Bookstore", "Education")
        db.session.commit()

    with dashboard_app.test_client() as client:
        response = client.get("/dashboard/8")

    assert response.status_code == 200
    assert b"Financial Insights" in response.data
    assert b"Biggest Money Destination" in response.data
