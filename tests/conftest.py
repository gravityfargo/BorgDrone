import os
import shutil
from random import randint

import pytest
from flask import Flask
from flask_login import LoginManager, current_user

from borgdrone import create_app
from borgdrone.auth import Users

INSTANCE_PATH = f"/tmp/borgdrone_pytest_{randint(0, 1000)}"


def new_instance_subdir() -> str:
    path = os.path.join(INSTANCE_PATH, str(randint(0, 1000)))
    os.mkdir(path)
    return path


@pytest.fixture(scope="session", name="app")
def ctx_app():
    os.environ["INSTANCE_PATH"] = INSTANCE_PATH
    app = create_app(enable_logging=False)

    yield app

    shutil.rmtree(INSTANCE_PATH)


@pytest.fixture(scope="session", name="runner")
def ctx_runner(app: Flask):
    """
    UNUSED
    creates a runner that can call Click commands
    """
    return app.test_cli_runner()


@pytest.fixture(scope="session", name="client")
def test_client(app: Flask):
    """
    Tests will use the client to make requests
    to the application without running the server.
    """
    login_manager = LoginManager()
    with app.test_client() as testing_client:
        # Establish an application context
        with app.app_context():

            @login_manager.user_loader
            def load_user(user_id):
                return Users.query.get(int(user_id))

            yield testing_client  # this is where the testing happens!


@pytest.fixture(scope="session", name="logged_in", autouse=True)
def test_login(app, client):
    form_data = {
        "username": app.config["DEFAULT_USER"],
        "password": app.config["DEFAULT_PASSWORD"],
        "remember": True,
    }

    result = client.post("/auth/login", data=form_data)
    assert result.headers["BORGDRONE_RETURN"] == "UserManager.login.SUCCESS"
    assert current_user.id == 1
