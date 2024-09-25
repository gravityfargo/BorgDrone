from flask.testing import FlaskClient

from borgdrone.borg import BorgRunner as borg_runner
from borgdrone.helpers import database, filemanager
from borgdrone.logging import logger
from borgdrone.repositories import Repository
from borgdrone.repositories import RepositoryManager as repository_manager

from .conftest import REPO_2


def test_get(client: FlaskClient):
    response = client.get("/repositories/")
    assert response.status_code == 200

    response = client.get("/repositories/import")
    assert response.status_code == 200

    response = client.get("/repositories/")
    assert response.status_code == 200

    repository = database.get_by_id(1, Repository)
    assert repository

    response = client.get("/repositories/create/")
    assert response.status_code == 200

    repository_manager.get_one(db_id=repository.id)
    repository_manager.get_one(repo_id=repository.repo_id)
    repository_manager.get_one(path=repository.path)
    repository_manager.get_all()


def test_create_repo_post(client: FlaskClient):
    # bad encryption type
    bad_encrpytion = REPO_2.copy()
    bad_encrpytion["encryption"] = "bad"
    response = client.post("/repositories/create/", data=bad_encrpytion)
    assert response.headers["BORGDRONE_RETURN"] == "RepositoryManager.create_repo.FAILURE"

    # bad path
    bad_path = REPO_2.copy()
    bad_path["path"] = "/bad/path"
    response = client.post("/repositories/create/", data=bad_path)
    assert response.headers["BORGDRONE_RETURN"] == "Borg.Repository.ParentPathDoesNotExist"

    # ok
    response = client.post("/repositories/create/", data=REPO_2)
    assert response.headers["BORGDRONE_RETURN"] == "RepositoryManager.create_repo.SUCCESS"

    # already exists
    response = client.post("/repositories/create/", data=REPO_2)
    assert response.headers["BORGDRONE_RETURN"] == "Borg.Repository.AlreadyExists"


def test_delete_repo(client: FlaskClient):
    # FAIL repository does not exist in db
    response = client.delete("/repositories/delete/3")
    assert response.headers["BORGDRONE_RETURN"] == "RepositoryManager.delete_repo.FAILURE"

    # OK deleted repo from previous test
    response = client.delete("/repositories/delete/2")
    assert response.headers["BORGDRONE_RETURN"] == "RepositoryManager.delete_repo.SUCCESS"


def test_repository_info(client: FlaskClient):
    repository = database.get_by_id(1, Repository)
    assert repository

    # OK
    response = client.post("/repositories/info", data={"path": repository.path})
    assert response.headers["BORGDRONE_RETURN"] == "RepositoryManager.get_repository_info.SUCCESS"
    # FAIL
    response = client.post("/repositories/info", data={"path": "/bad/path"})
    assert response.headers["BORGDRONE_RETURN"] == "Borg.Repository.DoesNotExist"


def test_import_repo(client: FlaskClient):
    result_log = borg_runner.create_repository(path=REPO_2["path"], encryption=REPO_2["encryption"])
    assert result_log.status == "SUCCESS"

    # OK POST
    response = client.post("/repositories/import", data={"path": REPO_2["path"]})
    assert response.headers["BORGDRONE_RETURN"] == "RepositoryManager.import_repo.SUCCESS"

    # FAIL repo already exists in db
    response = client.post("/repositories/import", data={"path": REPO_2["path"]})
    assert response.headers["BORGDRONE_RETURN"] == "RepositoryManager.import_repo.FAILURE"

    # FAIL repo does not exist
    response = client.post("/repositories/import", data={"path": "/bad/path"})
    assert response.headers["BORGDRONE_RETURN"] == "Borg.Repository.DoesNotExist"

    # delete the repository
    response = client.delete("/repositories/delete/2")
    assert response.headers["BORGDRONE_RETURN"] == "RepositoryManager.delete_repo.SUCCESS"


def test_update_stats(client: FlaskClient):
    repository = database.get_by_id(1, Repository)
    assert repository

    # OK
    response = client.post(f"/repositories/update/{repository.id}")
    assert response.headers["BORGDRONE_RETURN"] == "RepositoryManager.update_repository_info.SUCCESS"

    # FAIL | Failed to find repository.
    response = client.post("/repositories/update/0")
    assert response.headers["BORGDRONE_RETURN"] == "RepositoryManager.update_repository_info.FAILURE"
