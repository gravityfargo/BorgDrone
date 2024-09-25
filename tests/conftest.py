import os
import shutil
from random import randint
from typing import List

import pytest
from flask import Flask
from flask_login import LoginManager, current_user

from borgdrone import create_app
from borgdrone.auth import Users
from borgdrone.bundles import BackupBundle, BackupDirectory
from borgdrone.helpers import database, filemanager
from borgdrone.repositories import Repository

INSTANCE_PATH = f"/tmp/borgdrone_pytest_{randint(0, 1000)}"

TEST_PATHS_1 = [
    f"{INSTANCE_PATH}/exclude1",
    f"{INSTANCE_PATH}/exclude2",
    f"{INSTANCE_PATH}/include1",
    f"{INSTANCE_PATH}/include2",
]

TEST_PATHS_2 = [
    f"{INSTANCE_PATH}/exclude3",
    f"{INSTANCE_PATH}/exclude4",
    f"{INSTANCE_PATH}/include3",
    f"{INSTANCE_PATH}/include4",
]


def bundle_dir_data(client, exclude_paths: List[str], include_paths: List[str]) -> dict:
    form_data = {
        "cron_minute": "2",
        "cron_hour": "3",
        "cron_day": "4",
        "cron_month": "5",
        "cron_weekday": "6",
        "comment": "test comment",
    }

    def format_data(data) -> str:
        # path
        # permissions
        # owner
        # group
        # exclude
        path_data = f"""
            {data[3].decode("utf-8").strip()}
            {data[4].decode("utf-8").strip()}
            {data[5].decode("utf-8").strip()}
            {data[6].decode("utf-8").strip()}
            {data[7].decode("utf-8").strip()}
        """
        return path_data

    i = 0
    for path in exclude_paths:
        response = client.post("/bundles/check-dir/exclude", data={"exclude_path": path})
        data = response.data.splitlines()
        path_data = format_data(data)

        form_data[f"excludedir{i}"] = path_data
        i += 1

    for path in include_paths:
        filemanager.check_dir(path, create=True)
        response = client.post("/bundles/check-dir/include", data={"include_path": path})
        data = response.data.splitlines()
        path_data = format_data(data)

        form_data[f"includedir{i}"] = path_data
        i += 1

    return form_data


def new_instance_subdir() -> str:
    path = os.path.join(INSTANCE_PATH, str(randint(0, 1000)))
    os.mkdir(path)
    return path


@pytest.fixture(scope="session", name="app")
def ctx_app():
    os.environ["INSTANCE_PATH"] = INSTANCE_PATH
    app = create_app()
    for path in TEST_PATHS_1 + TEST_PATHS_2:
        os.makedirs(path, exist_ok=True)

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


@pytest.fixture(scope="session", name="repository")
def ctx_repo(client):
    repo = {
        "path": new_instance_subdir(),
        "encryption": "none",
    }
    # Session: the fixture is destroyed at the end of the session.
    client.post("/repositories/create/", data=repo)
    repository = database.get_latest(Repository)
    assert repository

    yield repository

    response = client.delete(f"/repositories/delete/{repository.id}")
    assert response.headers["BORGDRONE_RETURN"] == "RepositoryManager.delete_repo.SUCCESS"


@pytest.fixture(scope="function", name="bundle")
def ctx_bundle(client, repository):
    exclude_paths = [TEST_PATHS_1[0], TEST_PATHS_1[1]]
    include_paths = [TEST_PATHS_1[2], TEST_PATHS_1[3]]

    form_data = bundle_dir_data(client, exclude_paths, include_paths)

    # SUCCESS
    form_data["repo_db_id"] = repository.id
    response = client.post("/bundles/form/create", data=form_data)
    assert response.headers["BORGDRONE_RETURN"] == "BundleManager.process_bundle_form.SUCCESS"
    assert database.count(BackupBundle) > 0
    assert database.count(BackupDirectory) > 0

    bundle = database.get_latest(BackupBundle)
    assert bundle

    yield bundle, form_data

    response = client.delete(f"/bundles/delete/{bundle.id}")
