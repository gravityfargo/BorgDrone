import pytest

from borgdrone.borg import BorgRunner as borg_runner
from borgdrone.repositories import RepositoryManager as repository_manager

from ..conftest import new_instance_subdir

# TODO: seperate logger for testing formatting


@pytest.fixture(scope="function", name="repository")
def test_repo(client):
    repo = {
        "path": new_instance_subdir(),
        "encryption": "none",
    }
    # function: the fixture is destroyed at the end of the test.
    client.post("/repositories/create/", data=repo)
    result_log = repository_manager.get_latest()
    assert result_log.get_data()

    yield result_log.get_data()


def test_index_fail(client):
    response = client.get("/repositories/")
    assert response.status_code == 200
    # FAIL no repositories exist
    assert response.headers["BORGDRONE_RETURN"] == "RepositoryManager.get_all.FAILURE"


def test_index_success(client, repository):
    response = client.get("/repositories/")
    assert response.status_code == 200
    # SUCCESS a repository exists
    assert response.headers["BORGDRONE_RETURN"] == "RepositoryManager.get_all.SUCCESS"


def test_create_repo_get(client):
    response = client.get("/repositories/create/")
    assert response.status_code == 200


def test_create_repo_post(client):
    path = new_instance_subdir()
    repo1 = {
        "path": path,
        "encryption": "none",
    }
    # ok
    response = client.post("/repositories/create/", data=repo1)
    assert response.headers["BORGDRONE_RETURN"] == "RepositoryManager.create_repo.SUCCESS"

    # already exists
    response = client.post("/repositories/create/", data=repo1)
    assert response.headers["BORGDRONE_RETURN"] == "Borg.Repository.AlreadyExists"

    # bad encryption type
    path = new_instance_subdir()
    repo2 = {
        "path": path,
        "encryption": "notvalidtype",
    }
    response = client.post("/repositories/create/", data=repo2)
    assert response.headers["BORGDRONE_RETURN"] == "RepositoryManager.create_repo.FAILURE"

    # bad path
    repo3 = {
        "path": "/bad/path",
        "encryption": "none",
    }

    response = client.post("/repositories/create/", data=repo3)
    assert response.headers["BORGDRONE_RETURN"] == "Borg.Repository.ParentPathDoesNotExist"


def test_repository_info(client, repository):
    # OK
    response = client.post("/repositories/info", data={"path": repository.path})
    assert response.headers["BORGDRONE_RETURN"] == "RepositoryManager.get_repository_info.SUCCESS"
    # FAIL
    response = client.post("/repositories/info", data={"path": "/bad/path"})
    assert response.headers["BORGDRONE_RETURN"] == "Borg.Repository.DoesNotExist"


def test_delete_repo(client, repository):
    # OK
    response = client.delete(f"/repositories/delete/{repository.id}")
    assert response.headers["BORGDRONE_RETURN"] == "RepositoryManager.delete_repo.SUCCESS"

    # FAIL
    response = client.delete(f"/repositories/delete/{repository.id}")
    assert response.headers["BORGDRONE_RETURN"] == "RepositoryManager.delete_repo.FAILURE"


def test_import_repo(client):
    # pylint: disable=protected-access
    # create repo without adding to db
    path = new_instance_subdir()
    print(path)

    repo = {
        "path": path,
        "encryption": "none",
    }

    # OK GET
    response = client.get("/repositories/import")
    assert response.status_code == 200

    result_log = borg_runner.create_repository(path=repo["path"], encryption=repo["encryption"])
    assert result_log.status == "SUCCESS"

    # OK POST
    response = client.post("/repositories/import", data={"path": repo["path"]})
    assert response.headers["BORGDRONE_RETURN"] == "RepositoryManager.import_repo.SUCCESS"

    # FAIL
    response = client.post("/repositories/import", data={"path": repo["path"]})
    assert response.headers["BORGDRONE_RETURN"] == "RepositoryManager.import_repo.FAILURE"

    # FAIL
    response = client.post("/repositories/import", data={"path": "/bad/path"})
    assert response.headers["BORGDRONE_RETURN"] == "Borg.Repository.DoesNotExist"


def test_update_stats(client, repository):
    # OK
    response = client.post(f"/repositories/update/{repository.id}")
    assert response.headers["BORGDRONE_RETURN"] == "RepositoryManager.update_repository_info.SUCCESS"

    # FAIL
    response = client.post("/repositories/update/0")
    assert response.headers["BORGDRONE_RETURN"] == "RepositoryManager.update_repository_info.FAILURE"
