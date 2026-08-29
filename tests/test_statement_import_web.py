from io import BytesIO

from flask import Flask

from src.statement_import_web import register_statement_import


class FakeSession:
    def rollback(self):
        pass


class FakeDB:
    session = FakeSession()


class FakeTransaction:
    pass


def test_statement_import_route_is_registered():
    app = Flask(__name__, template_folder="../templates")
    app.secret_key = "test"
    register_statement_import(app, FakeDB(), FakeTransaction)

    with app.test_client() as client:
        response = client.get("/import")

    assert response.status_code == 200
    assert b"Bring your statement into Smart Spend AI" in response.data


def test_statement_import_rejects_unsupported_extension():
    app = Flask(__name__, template_folder="../templates")
    app.secret_key = "test"
    register_statement_import(app, FakeDB(), FakeTransaction)

    with app.test_client() as client:
        response = client.post(
            "/import",
            data={"statement": (BytesIO(b"hello"), "statement.txt")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )

    assert response.status_code == 200
    assert b"Unsupported file type" in response.data
