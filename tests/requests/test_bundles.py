# pylint: disable=W0611
from borgdrone.bundles import BackupBundle, BackupDirectory
from borgdrone.bundles import BundleManager as bundle_manager
from borgdrone.helpers import database

from ..conftest import TEST_PATHS_1, bundle_dir_data, ctx_repo


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

    # Duplicate bundles can exist.
    form_data["repo_db_id"] = repository.id
    response = client.post("/bundles/form/create", data=form_data)
    assert response.headers["BORGDRONE_RETURN"] == "BundleManager.process_bundle_form.SUCCESS"
    assert database.count(BackupBundle) == 2
    # Duplicate directories cannot exist.
    assert database.count(BackupDirectory) == 4

    # FAIL no includedirs
    fail_data = form_data.copy()
    for key in fail_data:
        if "include" in key:
            fail_data[key] = ""

    response = client.post("/bundles/form/create", data=fail_data)
    assert response.headers["BORGDRONE_RETURN"] == "BundleManager.process_bundle_form.FAILURE"


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


def test_bundle_update(client, bundle):
    bundle_instance, form_data = bundle

    form_data["comment"] = "updated comment"

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
    result_log = bundle_manager.create_backup(bundle_instance.id)
    assert result_log.status == "SUCCESS"
