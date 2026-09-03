from src.intelligence.categorizer import categorize_transaction


class FakeResult:
    rowcount = 1


class FakeUpdate:
    def __init__(self):
        self.where_clause = None
        self.updated_values = None

    def where(self, clause):
        self.where_clause = clause
        return self

    def values(self, **values):
        self.updated_values = values
        return self


class FakeSession:
    def __init__(self, transaction):
        self.transaction = transaction
        self.executed_statement = None
        self.committed = False

    def get(self, model, transaction_id):
        return self.transaction if transaction_id == self.transaction.id else None

    def execute(self, statement):
        self.executed_statement = statement
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


def test_user_correction_path_commits_without_reclassification(monkeypatch):
    """The attention correction uses a direct UPDATE, so the AI hook cannot overwrite it."""
    from flask import Flask
    import src.statement_import_web as statement_import_web
    from src.statement_import_web import register_statement_import

    app = Flask(__name__, template_folder="../templates")
    app.secret_key = "test"

    @app.route("/dashboard")
    def dashboard1():
        return "dashboard"

    db = FakeDB(FakeTransaction())

    def fake_update(model):
        return FakeUpdate()

    monkeypatch.setattr(statement_import_web, "update", fake_update)
    register_statement_import(app, db, FakeTransaction)

    with app.test_client() as client:
        response = client.post(
            "/dashboard/attention/7",
            data={"category": "Transfer / Personal", "next": "/dashboard"},
        )

    assert response.status_code == 302
    assert db.session.executed_statement is not None
    assert db.session.executed_statement.updated_values == {
        "category": "Transfer / Personal"
    }
    assert db.session.committed is True


def test_corrected_category_becomes_future_entity_history_evidence():
    """A concrete user correction should help future transactions for that entity."""
    history = [
        {"merchant_name": "COLLEGE BOOK SHOP", "category": "Transfer / Personal", "amount": 900, "note": "payment"},
        {"merchant_name": "COLLEGE BOOK SHOP", "category": "Transfer / Personal", "amount": 1100, "note": "payment"},
        {"merchant_name": "COLLEGE BOOK SHOP", "category": "Transfer / Personal", "amount": 950, "note": "payment"},
        {"merchant_name": "COLLEGE BOOK SHOP", "category": "Transfer / Personal", "amount": 1000, "note": "payment"},
    ]

    result = categorize_transaction("COLLEGE BOOK SHOP", 1050, "payment", "UPI", history)

    assert result["category"] == "Transfer / Personal"
    assert result["status"] == "categorized"
    assert result["needs_user_confirmation"] is False
    assert result["entity_memory"]["memory_label"] == "STABLE"
    assert result["entity_memory"]["dominant_category"] == "Transfer / Personal"


def test_unknown_does_not_teach_entity_memory():
    """Unresolved transactions must not become training data for entity memory."""
    history = [
        {"merchant_name": "RAHUL KUMAR", "category": "Unknown", "amount": 500, "note": "payment"}
    ]

    result = categorize_transaction("RAHUL KUMAR", 700, "payment", "UPI", history)

    assert result["entity_memory"]["category_counts"] == {}
    assert result["entity_memory"]["memory_label"] == "UNKNOWN"
