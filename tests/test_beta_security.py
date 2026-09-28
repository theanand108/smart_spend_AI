from flask import Flask

from src.statement_import_web import register_statement_import


class FakeDB:
    session = object()


class FakeTransaction:
    pass


def make_security_app():
    app = Flask(__name__)
    app.secret_key = "test"

    @app.route("/login")
    def login():
        return "login"

    @app.route("/dashboard")
    def dashboard1():
        return "private dashboard"

    @app.route("/simulateATransaction")
    def simulate_transaction():
        return "private transactions"

    register_statement_import(app, FakeDB(), FakeTransaction)
    return app


def test_dashboard_redirects_when_not_authenticated():
    app = make_security_app()

    with app.test_client() as client:
        response = client.get("/dashboard")

    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login?next=/dashboard")


def test_simulator_redirects_when_not_authenticated():
    app = make_security_app()

    with app.test_client() as client:
        response = client.get("/simulateATransaction")

    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login?next=/simulateATransaction")


def test_authenticated_financial_page_gets_security_headers_and_no_store():
    app = make_security_app()

    with app.test_client() as client:
        with client.session_transaction() as flask_session:
            flask_session["user_id"] = 1

        response = client.get("/dashboard")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"
    assert response.headers["Cache-Control"] == "private, no-store"
