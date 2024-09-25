# pylint: disable=W0611
from flask.testing import FlaskClient

from borgdrone.archives import Archive
from borgdrone.bundles import BackupBundle, BackupDirectory
from borgdrone.bundles import BundleManager as bundle_manager
from borgdrone.helpers import database
from borgdrone.logging import logger
from borgdrone.repositories import Repository

from .conftest import bundle_form_data


def test_get(client: FlaskClient):
    response = client.get("/bundles/")
    assert response.status_code == 200

    response = client.get("/bundles/form/create")
    assert response.status_code == 200

    bundle = database.get_by_id(1, BackupBundle)
    assert bundle

    # SUCCESS bundle_form update
    response = client.get(f"/bundles/form/update/{bundle.id}")
    assert response.status_code == 200

    # FAIL bundle_form update | does not exist
    response = client.get("/bundles/form/update/0")
    assert response.status_code == 200

    # SUCCESS run_backup
    response = client.get(f"/bundles/{bundle.id}/run")
    assert response.status_code == 200

    # FAIL run_backup | does not exist
    response = client.get("/bundles/0/run")
    assert response.status_code == 200

    bundle_manager.get_one(bundle_id=bundle.id)
    bundle_manager.get_one(repo_id=bundle.repo_id)
    bundle_manager.get_one(command_line=bundle.command_line)
    bundle_manager.get_all(bundle.repo_id)

    result_log = bundle_manager.check_dir("/bad/path")
    assert result_log.status == "FAILURE"


def test_create_bundle(client: FlaskClient):
    form_data = bundle_form_data(2)
    repository = database.get_latest(Repository)
    assert repository

    # SUCCESS
    form_data["repo_db_id"] = str(repository.id)
    response = client.post("/bundles/form/create", data=form_data)
    assert response.headers["BORGDRONE_RETURN"] == "BundleManager.process_bundle_form.SUCCESS"
    assert database.count(BackupBundle) == 2
    assert database.count(BackupDirectory) == 8

    # Duplicate bundles can exist.
    response = client.post("/bundles/form/create", data=form_data)
    assert database.count(BackupBundle) == 3
    assert database.count(BackupDirectory) == 8  # Duplicate directories cannot exist.

    bundle = database.get_latest(BackupBundle)
    assert bundle

    # deleting one should not delete shared backupdirectories
    response = client.delete(f"/bundles/delete/{bundle.id}")
    assert response.headers["BORGDRONE_RETURN"] == "BundleManager.delete_bundle.SUCCESS"
    assert database.count(BackupBundle) == 2
    assert database.count(BackupDirectory) == 8

    # FAIL no includedirs
    fail_form_data = form_data.copy()
    for key in form_data:
        if key.startswith("includedir"):
            fail_form_data.pop(key)

    response = client.post("/bundles/form/create", data=fail_form_data)
    assert response.headers["BORGDRONE_RETURN"] == "BundleManager.process_bundle_form.FAILURE"

    bundle = database.get_latest(BackupBundle)
    assert bundle

    response = client.delete(f"/bundles/delete/{bundle.id}")
    assert response.headers["BORGDRONE_RETURN"] == "BundleManager.delete_bundle.SUCCESS"
    assert database.count(BackupBundle) == 1
    assert database.count(BackupDirectory) == 4

    result = bundle_manager.process_bundle_form(purpose="invalid")
    assert result.status == "FAILURE"


def test_bundle_update(client: FlaskClient):
    form_data = bundle_form_data(2)

    # invalid bundle
    response = client.post("/bundles/form/update/0", data=form_data)
    assert response.headers["BORGDRONE_RETURN"] == "BundleManager.process_bundle_form.FAILURE"

    bundle = database.get_latest(BackupBundle)
    assert bundle

    form_data["comment"] = "updated comment"
    form_data["bundle_id"] = str(bundle.id)

    response = client.post(f"/bundles/form/update/{bundle.id}", data=form_data)
    assert response.headers["BORGDRONE_RETURN"] == "BundleManager.process_bundle_form.SUCCESS"


def test_bundle_delete(client: FlaskClient):
    # FAIL delete_bundle | does not exist
    response = client.delete("/bundles/delete/0")
    assert response.headers["BORGDRONE_RETURN"] == "BundleManager.delete_bundle.FAILURE"


def test_create_backup(client: FlaskClient):
    bundle = database.get_latest(BackupBundle)
    assert bundle

    archive_count = database.count(Archive)
    result_log = bundle_manager.create_backup(bundle.id)

    assert result_log.status == "SUCCESS"
    assert database.count(Archive) == archive_count + 1
