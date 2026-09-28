from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from app import Transaction, User, app, db


@pytest.fixture
def dashboard_app(tmp_path):
    db_path = tmp_path / "dashboard.db"
    real_db_path = Path(app.root_path) / "instance" / "smart_spend.db"
    original_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    app.config["TESTING"] = True
    temporary_uri = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_DATABASE_URI"] = temporary_uri

    with app.app_context():
        engines = db.engines
        original_engines = engines.copy()
        temporary_engine = create_engine(temporary_uri)
        engines[None] = temporary_engine
        try:
            assert app.config["SQLALCHEMY_DATABASE_URI"] == temporary_uri
            assert engines[None].url.database == str(db_path)
            assert Path(engines[None].url.database).resolve() != real_db_path.resolve()
            db.drop_all()
            db.create_all()
            db.session.add(User(email="dashboard-test@example.com", password_hash="test"))
            db.session.commit()
            yield app
        finally:
            db.session.remove()
            db.drop_all()
            temporary_engine.dispose()
            engines.clear()
            engines.update(original_engines)
            app.config["SQLALCHEMY_DATABASE_URI"] = original_uri


def authenticate(client, user_id=1):
    with client.session_transaction() as flask_session:
        flask_session["user_id"] = user_id
        flask_session["_csrf_token"] = "test-csrf-token"


def add_transaction(month, amount, merchant, category, day=1, user_id=1):
    db.session.add(
        Transaction(
            date=datetime(datetime.now().year, month, day),
            merchant_name=merchant,
            amount=amount,
            category=category,
            payment_method="UPI",
            user_id=user_id,
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
        authenticate(client)
        response = client.get("/dashboard/8")

    html = response.data.decode("utf-8")
    assert response.status_code == 200
    assert "Financial Insights" in html
    assert "A spending area jumped" in html
    assert "Food &amp; Dining" in html
    assert "+₹1,000" in html
    assert "Spending changed by ₹1,000 (100%)" in html
    assert "Education" in html


def test_dashboard_preserves_v1_three_card_composition(dashboard_app):
    with dashboard_app.app_context():
        seed_structured_insight_transactions()

    with dashboard_app.test_client() as client:
        authenticate(client)
        response = client.get("/dashboard/8")

    html = response.data.decode("utf-8")
    assert html.count("insight-card-primary") == 1
    assert html.count("insight-card-secondary") == 2


def test_search_filter_does_not_change_financial_insights(dashboard_app):
    with dashboard_app.app_context():
        seed_structured_insight_transactions()

    with dashboard_app.test_client() as client:
        authenticate(client)
        response = client.get("/dashboard/8?q=Bookstore")

    html = response.data.decode("utf-8")
    assert response.status_code == 200
    assert "Bookstore" in html
    assert "A spending area jumped" in html
    assert "Food &amp; Dining" in html
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
        authenticate(client)
        response = client.get("/dashboard/8")

    assert response.status_code == 200
    assert b"Financial Insights" in response.data
    assert b"Biggest Money Destination" in response.data
    assert response.data.count(b"insight-card-primary") == 1
    assert response.data.count(b"insight-card-secondary") == 2


def test_dashboard_does_not_expose_another_users_transactions(dashboard_app):
    with dashboard_app.app_context():
        db.session.add(User(email="other-user@example.com", password_hash="test"))
        db.session.flush()
        add_transaction(8, 250, "USER ONE MERCHANT", "Food & Dining", user_id=1)
        add_transaction(8, 9999, "USER TWO SECRET MERCHANT", "Shopping", user_id=2)
        db.session.commit()

    with dashboard_app.test_client() as client:
        authenticate(client, user_id=1)
        response = client.get("/dashboard/8")

    assert response.status_code == 200
    assert b"USER ONE MERCHANT" in response.data
    assert b"USER TWO SECRET MERCHANT" not in response.data
    assert b"9,999" not in response.data


def test_user_cannot_delete_another_users_transaction(dashboard_app):
    with dashboard_app.app_context():
        db.session.add(User(email="other-user@example.com", password_hash="test"))
        db.session.flush()
        add_transaction(8, 9999, "USER TWO SECRET MERCHANT", "Shopping", user_id=2)
        db.session.commit()
        transaction_id = Transaction.query.filter_by(user_id=2).first().id

    with dashboard_app.test_client() as client:
        authenticate(client, user_id=1)
        response = client.post(
            f"/delete/{transaction_id}",
            data={"_csrf_token": "test-csrf-token", "next": "/dashboard"},
        )

    assert response.status_code == 302
    with dashboard_app.app_context():
        transaction = db.session.get(Transaction, transaction_id)
        assert transaction is not None
        assert transaction.user_id == 2


def test_user_cannot_update_another_users_transaction(dashboard_app):
    with dashboard_app.app_context():
        db.session.add(User(email="other-user@example.com", password_hash="test"))
        db.session.flush()
        add_transaction(8, 9999, "USER TWO SECRET MERCHANT", "Shopping", user_id=2)
        db.session.commit()
        transaction_id = Transaction.query.filter_by(user_id=2).first().id

    with dashboard_app.test_client() as client:
        authenticate(client, user_id=1)
        response = client.post(
            f"/update/{transaction_id}",
            data={
                "_csrf_token": "test-csrf-token",
                "merchant_name": "ATTACKED MERCHANT",
                "amount": "1",
                "notes": "attacker",
                "payment_method": "UPI",
                "next": "/dashboard",
            },
        )

    assert response.status_code == 302
    with dashboard_app.app_context():
        transaction = db.session.get(Transaction, transaction_id)
        assert transaction is not None
        assert transaction.user_id == 2
        assert transaction.merchant_name == "USER TWO SECRET MERCHANT"
        assert transaction.amount == 9999
        assert transaction.category == "Shopping"


def test_user_export_contains_only_their_transactions(dashboard_app):
    with dashboard_app.app_context():
        db.session.add(User(email="other-user@example.com", password_hash="test"))
        db.session.flush()
        add_transaction(8, 250, "USER ONE MERCHANT", "Food & Dining", user_id=1)
        add_transaction(8, 9999, "USER TWO SECRET MERCHANT", "Shopping", user_id=2)
        db.session.commit()

    with dashboard_app.test_client() as client:
        authenticate(client, user_id=1)
        response = client.get("/export/8")

    assert response.status_code == 200
    assert b"USER ONE MERCHANT" in response.data
    assert b"USER TWO SECRET MERCHANT" not in response.data
    assert b"9999" not in response.data
