from src.intelligence.categorizer import categorize_transaction


class FakeResult:
    rowcount = 1


class FakeSession:
    def __init__(self, transaction):
        self.transaction = transaction
        self.updated_values = None
        self.committed = False

    def get(self, model, transaction_id):
        return self.transaction if transaction_id == self.transaction.id else None

    def execute(self, statement):
        self.updated_values = statement
        return FakeResult()

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


class FakeDB:
    def __init__(self, transaction):
        self.session = FakeSession(transaction)


class FakeTransaction:
    id = 7
    merchant_name = "College Book Shop"


def test_user_correction_is_written_as_authoritative_category():
    """The attention correction path must write the selected category directly."""
    from flask import Flask
    from src.statement_import_web import register_statement_import

    app = Flask(__name__, template_folder="../templates")
    app.secret_key = "test"

    @app.route("/dashboard")
    def dashboard1():
        return "dashboard"

    db = FakeDB(FakeTransaction())
    register_statement_import(app, db, FakeTransaction)

    with app.test_client() as client:
        response = client.post(
            "/dashboard/attention/7",
            data={"category": "Education", "next": "/dashboard"},
        )

    assert response.status_code == 302
    assert db.session.updated_values is not None
    assert db.session.committed is True


def test_corrected_category_becomes_future_entity_history_evidence():
    """A concrete user correction should help future transactions for that entity."""
    history = [
        {
            "merchant_name": "COLLEGE BOOK SHOP",
            "category": "Education",
            "amount": 900,
            "note": "textbook purchase",
        },
        {
            "merchant_name": "COLLEGE BOOK SHOP",
            "category": "Education",
            "amount": 1100,
            "note": "notebook and stationery",
        },
        {
            "merchant_name": "COLLEGE BOOK SHOP",
            "category": "Education",
            "amount": 950,
            "note": "college books",
        },
        {
            "merchant_name": "COLLEGE BOOK SHOP",
            "category": "Education",
            "amount": 1000,
            "note": "stationery for semester",
        },
    ]

    result = categorize_transaction(
        "COLLEGE BOOK SHOP",
        1050,
        "payment",
        "UPI",
        history,
    )

    assert result["category"] == "Education"
    assert result["status"] == "categorized"
    assert result["needs_user_confirmation"] is False
    assert result["entity_memory"]["memory_label"] == "STABLE"
    assert result["entity_memory"]["dominant_category"] == "Education"


def test_unknown_correction_does_not_teach_entity_memory():
    history = [
        {
            "merchant_name": "RAHUL KUMAR",
            "category": "Unknown",
            "amount": 500,
            "note": "payment",
        }
    ]

    result = categorize_transaction(
        "RAHUL KUMAR",
        700,
        "payment",
        "UPI",
        history,
    )

    assert result["entity_memory"]["category_counts"] == {}
    assert result["entity_memory"]["memory_label"] == "UNKNOWN"
