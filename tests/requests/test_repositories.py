from borgdrone.borg import BorgRunner as borg_runner

from ..conftest import ctx_repo, new_instance_subdir


def test_get(client):
    # FAIL no repositories exist
    response = client.get("/repositories/")
    assert response.status_code == 200
    assert response.headers["BORGDRONE_RETURN"] == "RepositoryManager.get_all.FAILURE"

    # OK GET
    response = client.get("/repositories/import")
    assert response.status_code == 200


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


def test_delete_repo_fail(client):
    # FAIL
    response = client.delete("/repositories/delete/0")
    assert response.headers["BORGDRONE_RETURN"] == "RepositoryManager.delete_repo.FAILURE"


def test_import_repo(client):
    # pylint: disable=protected-access
    # create repo without adding to db
    path = new_instance_subdir()

    repo = {
        "path": path,
        "encryption": "none",
    }

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

    # FAIL | Failed to find repository.
    response = client.post("/repositories/update/0")
    assert response.headers["BORGDRONE_RETURN"] == "RepositoryManager.update_repository_info.FAILURE"
