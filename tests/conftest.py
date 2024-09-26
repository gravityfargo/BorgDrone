import os
import shutil
from random import randint
from typing import List

import pytest
from flask import Flask
from flask.testing import FlaskClient
from flask_login import LoginManager, current_user

from borgdrone import create_app
from borgdrone.archives import Archive
from borgdrone.archives import ArchivesManager as archives_manager
from borgdrone.auth import Users
from borgdrone.bundles import BackupBundle, BackupDirectory
from borgdrone.bundles import BundleManager as bundle_manager
from borgdrone.helpers import database, filemanager
from borgdrone.logging import logger
from borgdrone.repositories import Repository

INSTANCE_PATH = "/tmp/borgdrone_pytest"

REPO_1 = {
    "path": "/tmp/borgdrone_pytest/TestRepo1",
    "encryption": "none",
}
REPO_2 = {
    "path": "/tmp/borgdrone_pytest/TestRepo2",
    "encryption": "none",
}

TEST_DATA_PATH = "/tmp/borgdrone_pytest/data"

INCLUDE_PATHS_1 = [
    f"{TEST_DATA_PATH}/include1",
    f"{TEST_DATA_PATH}/include2",
]

INCLUDE_PATHS_2 = [
    f"{TEST_DATA_PATH}/include3",
    f"{TEST_DATA_PATH}/include4",
]

EXCLUDE_PATHS_1 = [
    f"{TEST_DATA_PATH}/exclude1",
    f"{TEST_DATA_PATH}/exclude2",
]

EXCLUDE_PATHS_2 = [
    f"{TEST_DATA_PATH}/exclude3",
    f"{TEST_DATA_PATH}/exclude4",
]

"""
Notes:
scope="session" -> the fixture is destroyed at the end of the session.

Starting Environment:
- a repository not in the database

Functional contexts:
from flask import current_app as app

"""


@pytest.fixture(scope="session")
def app():

    os.environ["INSTANCE_PATH"] = INSTANCE_PATH
    os.environ["PYTESTING"] = "True"

    ctx_app = create_app()
    for directory in [TEST_DATA_PATH] + INCLUDE_PATHS_1 + INCLUDE_PATHS_2 + EXCLUDE_PATHS_1 + EXCLUDE_PATHS_2:
        # create the directory and add a 4kb file
        filemanager.check_dir(directory, create=True)
        file_path = f"{directory}/4kb_test_data.txt"
        size_in_kb = 4
        data = os.urandom(size_in_kb * 1024)
        with open(file_path, "wb") as file:
            file.write(data)

    yield ctx_app

    shutil.rmtree(INSTANCE_PATH)


@pytest.fixture
def runner(app: Flask):
    """
    UNUSED
    creates a runner that can call Click commands
    """
    return app.test_cli_runner()


@pytest.fixture(scope="session")
def client(app: Flask):
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

            yield testing_client


@pytest.fixture(scope="session", autouse=True)
def ctx_login(app: Flask, client: FlaskClient):
    """Should always be logged in for tests"""
    form_data = {
        "username": app.config["DEFAULT_USER"],
        "password": app.config["DEFAULT_PASSWORD"],
        "remember": True,
    }

    result = client.post("/auth/login", data=form_data)
    assert result.headers["BORGDRONE_RETURN"] == "UserManager.login.SUCCESS"
    assert current_user.id == 1


@pytest.fixture(scope="session", autouse=True)
def ctx_repository(client: FlaskClient, ctx_login):
    """Create a repository for testing"""

    response = client.post("/repositories/create/", data=REPO_1)
    assert response.headers["BORGDRONE_RETURN"] == "RepositoryManager.create_repo.SUCCESS"

    repository = database.get_latest(Repository)
    assert repository

    yield


def bundle_form_data(number: int):
    if number == 1:
        include_paths = INCLUDE_PATHS_1
        exclude_paths = EXCLUDE_PATHS_1
    else:
        include_paths = INCLUDE_PATHS_2
        exclude_paths = EXCLUDE_PATHS_2

    form_data = {
        "cron_minute": "2",
        "cron_hour": "3",
        "cron_day": "4",
        "cron_month": "5",
        "cron_weekday": "6",
        "comment": "test comment",
    }

    for path in include_paths:
        data = bundle_manager.check_dir(path)
        dir_data = data.get_data()
        assert dir_data
        path_data = f"""
            path: {path}
            permissions: {dir_data[0]}
            owner: {dir_data[1]}
            group: {dir_data[2]}
            exclude: False
        """
        form_data[f"includedir{randint(0, 1000)}"] = path_data

    for path in exclude_paths:
        data = bundle_manager.check_dir(path)
        dir_data = data.get_data()
        assert dir_data
        path_data = f"""
            path: {path}
            permissions: {dir_data[0]}
            owner: {dir_data[1]}
            group: {dir_data[2]}
            exclude: True
        """
        form_data[f"excludedir{randint(0, 1000)}"] = path_data

    return form_data


@pytest.fixture(scope="session", autouse=True)
def ctx_bundle(client: FlaskClient, ctx_repository):
    form_data = bundle_form_data(1)

    repository = database.get_latest(Repository)
    assert repository

    # SUCCESS
    form_data["repo_db_id"] = f"{repository.id}"
    response = client.post("/bundles/form/create", data=form_data)
    assert response.headers["BORGDRONE_RETURN"] == "BundleManager.process_bundle_form.SUCCESS"
    assert database.count(BackupBundle) > 0
    assert database.count(BackupDirectory) > 0

    bundle = database.get_latest(BackupBundle)
    assert bundle

    yield bundle


@pytest.fixture(scope="function", name="archive")
def ctx_archive(client: FlaskClient, ctx_bundle):
    bundle = database.get_latest(BackupBundle)
    assert bundle

    start_archive_count = database.count(Archive)

    result_log = bundle_manager.create_backup(bundle.id)
    assert result_log.status == "SUCCESS"
    assert database.count(Archive) == start_archive_count + 1

    archive = database.get_latest(Archive)
    assert archive
    yield archive

    result_log = archives_manager.delete_archive(archive.name)
    assert result_log.status == "SUCCESS"
    assert database.count(Archive) == start_archive_count
