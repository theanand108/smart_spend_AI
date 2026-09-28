from flask import Flask

from src.statement_import_web import register_statement_import


class FakeDB:
    class Session:
        pass

    session = Session()


class FakeTransaction:
    pass


def make_demo_app():
    app = Flask(__name__, template_folder="../templates")
    app.secret_key = "test"
    register_statement_import(app, FakeDB(), FakeTransaction)
    return app


def test_demo_dashboard_is_public_and_read_only():
    app = make_demo_app()

    with app.test_client() as client:
        response = client.get("/demo")

    assert response.status_code == 200
    assert b"sample dashboard using fictional data" in response.data
    assert b"Food &amp; Dining" in response.data


def test_demo_dashboard_does_not_require_authentication():
    app = make_demo_app()

    with app.test_client() as client:
        response = client.get("/demo")

    assert response.status_code == 200
    assert response.headers.get("Location") is None
