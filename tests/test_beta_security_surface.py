from flask import Flask

from src.statement_import_web import register_statement_import


class FakeDB:
    session = object()


class FakeTransaction:
    pass


def make_security_surface_app():
    app = Flask(__name__)
    app.secret_key = "test"

    @app.route("/login")
    def login():
        return "login"

    @app.route("/dashboard")
    @app.route("/dashboard/<int:month>")
    def dashboard1(month=None):
        return "private dashboard"

    @app.route("/simulateATransaction")
    def simulate_transaction():
        return "private transactions"

    register_statement_import(app, FakeDB(), FakeTransaction)
    return app


def test_all_financial_workspace_pages_redirect_when_not_authenticated():
    app = make_security_surface_app()
    protected_requests = (
        ("get", "/dashboard"),
        ("get", "/dashboard/9"),
        ("get", "/simulateATransaction"),
        ("get", "/import"),
        ("get", "/dashboard/attention"),
        ("post", "/dashboard/attention/123"),
    )

    with app.test_client() as client:
        for method, path in protected_requests:
            response = getattr(client, method)(path)
            assert response.status_code == 302
            assert response.headers["Location"].startswith("/login?next=")


def test_financial_workspace_redirect_preserves_internal_path_only():
    app = make_security_surface_app()

    with app.test_client() as client:
        response = client.post("/dashboard/attention/123?month=9")

    assert response.status_code == 302
    assert response.headers["Location"] == "/login?next=/dashboard/attention/123?month=9"
