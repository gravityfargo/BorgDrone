# pylint: disable=W0611
from borgdrone.archives import Archive
from borgdrone.bundles import BackupBundle, BackupDirectory
from borgdrone.bundles import BundleManager as bundle_manager
from borgdrone.helpers import database
from borgdrone.logging import logger

from ..conftest import TEST_PATHS_1, bundle_dir_data, ctx_repo


def test_get(client, logged_in, bundle):
    response = client.get("/bundles/")
    assert response.status_code == 200

    response = client.get("/bundles/form/create")
    assert response.status_code == 200

    bundle_instance, _ = bundle
    # SUCCESS bundle_form update
    response = client.get(f"/bundles/form/update/{bundle_instance.id}")
    assert response.status_code == 200

    # FAIL bundle_form update | does not exist
    response = client.get("/bundles/form/update/0")
    assert response.status_code == 200

    # SUCCESS run_backup
    response = client.get(f"/bundles/{bundle_instance.id}/run")
    assert response.status_code == 200

    # FAIL run_backup | does not exist
    response = client.get("/bundles/0/run")
    assert response.status_code == 200

    bundle_manager.get_one(bundle_id=bundle_instance.id)
    bundle_manager.get_one(repo_id=bundle_instance.repo_id)
    bundle_manager.get_one(command_line=bundle_instance.command_line)
    bundle_manager.get_all(bundle_instance.repo_id)


def test_create_bundle(client, repository):
    exclude_paths = [TEST_PATHS_1[0], TEST_PATHS_1[1]]
    include_paths = [TEST_PATHS_1[2], TEST_PATHS_1[3]]

    form_data = bundle_dir_data(client, exclude_paths, include_paths)

    # SUCCESS
    form_data["repo_db_id"] = repository.id
    response = client.post("/bundles/form/create", data=form_data)
    assert response.headers["BORGDRONE_RETURN"] == "BundleManager.process_bundle_form.SUCCESS"
    assert database.count(BackupBundle) == 1
    assert database.count(BackupDirectory) == 4

    bundle_instance = database.get_latest(BackupBundle)
    assert bundle_instance
    assert len(bundle_instance.backupdirectories) == 4

    # Duplicate bundles can exist.
    response = client.post("/bundles/form/create", data=form_data)
    assert database.count(BackupBundle) == 2
    assert database.count(BackupDirectory) == 4  # Duplicate directories cannot exist.

    # deleting one should not delete shared backupdirectories
    response = client.delete(f"/bundles/delete/{bundle_instance.id}")
    assert response.headers["BORGDRONE_RETURN"] == "BundleManager.delete_bundle.SUCCESS"
    assert database.count(BackupBundle) == 1
    assert database.count(BackupDirectory) == 4

    # FAIL no includedirs
    fail_form_data = form_data.copy()
    for key in form_data:
        if key.startswith("includedir"):
            fail_form_data.pop(key)

    response = client.post("/bundles/form/create", data=fail_form_data)
    assert response.headers["BORGDRONE_RETURN"] == "BundleManager.process_bundle_form.FAILURE"

    bundle_instance = database.get_latest(BackupBundle)
    assert bundle_instance
    response = client.delete(f"/bundles/delete/{bundle_instance.id}")
    assert response.headers["BORGDRONE_RETURN"] == "BundleManager.delete_bundle.SUCCESS"
    assert database.count(BackupBundle) == 0
    assert database.count(BackupDirectory) == 0

    result = bundle_manager.process_bundle_form(purpose="invalid")
    assert result.status == "FAILURE"


def test_bundle_update(client, bundle):
    bundle_instance, form_data = bundle

    form_data["comment"] = "updated comment"
    form_data["bundle_id"] = bundle_instance.id

    response = client.post(f"/bundles/form/update/{bundle_instance.id}", data=form_data)
    assert response.headers["BORGDRONE_RETURN"] == "BundleManager.process_bundle_form.SUCCESS"
    assert response.status_code == 200


def test_bundle_delete(client, bundle):
    bundle_instance, _ = bundle
    # SUCCESS delete_bundle
    response = client.delete(f"/bundles/delete/{bundle_instance.id}")
    assert response.headers["BORGDRONE_RETURN"] == "BundleManager.delete_bundle.SUCCESS"

    # FAIL delete_bundle | does not exist
    response = client.delete("/bundles/delete/0")
    assert response.headers["BORGDRONE_RETURN"] == "BundleManager.delete_bundle.FAILURE"


def test_create_backup(client, bundle):
    bundle_instance, _ = bundle
    archive_count = database.count(Archive)
    result_log = bundle_manager.create_backup(bundle_instance.id)
    assert result_log.status == "SUCCESS"
    assert database.count(Archive) == archive_count + 1
