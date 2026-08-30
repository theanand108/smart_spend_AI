from datetime import datetime

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from src.intelligence.categorizer import categorize_transaction
from src.statement_import_web import register_statement_import


def make_app():
    app = Flask(__name__, template_folder="../templates")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.secret_key = "test"
    db = SQLAlchemy(app)

    class Transaction(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        date = db.Column(db.DateTime, nullable=False)
        merchant_name = db.Column(db.String, nullable=False)
        amount = db.Column(db.Float, nullable=False)
        category = db.Column(db.String(50))
        payment_method = db.Column(db.String(50))
        notes = db.Column(db.String(200))

    @app.route("/dashboard")
    def dashboard1():
        return "dashboard"

    register_statement_import(app, db, Transaction)
    with app.app_context():
        db.create_all()
        db.session.add_all(
            [
                Transaction(
                    date=datetime(2026, 8, 30),
                    merchant_name="EKART",
                    amount=673,
                    category="Unknown",
                    payment_method="UPI",
                ),
                Transaction(
                    date=datetime(2026, 8, 30),
                    merchant_name="DEEPAK FRUIT CENTRE",
                    amount=200,
                    category="Groceries",
                    payment_method="UPI",
                ),
            ]
        )
        db.session.commit()

    return app, db, Transaction


def test_dashboard_attention_partial_contains_only_unresolved_transactions():
    app, _db, _transaction = make_app()

    with app.test_client() as client:
        response = client.get("/dashboard/attention?month=8")

    assert response.status_code == 200
    assert b"Needs your attention" in response.data
    assert b"EKART" in response.data
    assert b"DEEPAK FRUIT CENTRE" not in response.data


def test_dashboard_attention_correction_persists_category():
    app, db, Transaction = make_app()

    # Flask-SQLAlchemy's scoped session requires an active application context
    # for ORM queries. Perform the lookup inside one before exercising the route.
    with app.app_context():
        transaction_id = Transaction.query.filter_by(merchant_name="EKART").first().id

    with app.test_client() as client:
        response = client.post(
            f"/dashboard/attention/{transaction_id}",
            data={"category": "Shopping", "next": "/dashboard"},
        )

    assert response.status_code == 302
    with app.app_context():
        transaction = db.session.get(Transaction, transaction_id)
        assert transaction.category == "Shopping"


def test_dashboard_attention_correction_becomes_future_history_evidence():
    app, db, Transaction = make_app()

    with app.app_context():
        transaction_id = Transaction.query.filter_by(merchant_name="EKART").first().id

    with app.test_client() as client:
        response = client.post(
            f"/dashboard/attention/{transaction_id}",
            data={"category": "Shopping", "next": "/dashboard"},
        )

    assert response.status_code == 302

    with app.app_context():
        rows = Transaction.query.order_by(Transaction.id).all()
        history = [
            {
                "merchant_name": row.merchant_name,
                "category": row.category,
                "amount": row.amount,
                "note": row.notes,
            }
            for row in rows
        ]

    future = categorize_transaction("EKART", 673, None, "UPI", history)
    assert future["category"] == "Shopping"
    assert future["status"] == "categorized"
    assert future["needs_user_confirmation"] is False
