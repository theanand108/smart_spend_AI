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


def make_test_app():
    app = Flask(__name__, template_folder="../templates")
    app.secret_key = "test"

    # The import template links back to the application's dashboard endpoint.
    # Provide a minimal stand-in so the blueprint can be tested independently
    # from the full Flask application.
    @app.route("/dashboard")
    def dashboard1():
        return "dashboard"

    register_statement_import(app, FakeDB(), FakeTransaction)
    return app


def test_statement_import_route_is_registered():
    app = make_test_app()

    with app.test_client() as client:
        response = client.get("/import")

    assert response.status_code == 200
    assert b"Bring your statement into Smart Spend AI" in response.data


def test_statement_import_rejects_unsupported_extension():
    app = make_test_app()

    with app.test_client() as client:
        response = client.post(
            "/import",
            data={"statement": (BytesIO(b"hello"), "statement.txt")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )

    assert response.status_code == 200
    assert b"Unsupported file type" in response.data
