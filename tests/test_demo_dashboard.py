from flask import Flask

from src.demo_dashboard import register_demo_dashboard


def test_demo_dashboard_is_public_and_read_only():
    app = Flask(__name__, template_folder="../templates")
    app.secret_key = "test"
    register_demo_dashboard(app)

    with app.test_client() as client:
        response = client.get("/demo")

    assert response.status_code == 200
    assert b"sample dashboard using fictional data" in response.data
    assert b"Food &amp; Dining" in response.data


def test_demo_dashboard_does_not_require_authentication():
    app = Flask(__name__, template_folder="../templates")
    app.secret_key = "test"
    register_demo_dashboard(app)

    with app.test_client() as client:
        response = client.get("/demo")

    assert response.status_code == 200
    assert response.headers.get("Location") is None
