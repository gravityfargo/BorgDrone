import pytest
from flask_login import current_user

from borgdrone.bundles import BundleManager
from borgdrone.helpers import filemanager
from borgdrone.repositories import RepositoryManager

from ..conftest import INSTANCE_PATH
from .test_repositories import test_repo


@pytest.fixture(scope="function", name="bundle")
def test_bundle(client, repository):
    form_data = {
        "repo_id": repository.id,
        "cron_minute": "2",
        "cron_hour": "3",
        "cron_day": "4",
        "cron_month": "5",
        "cron_weekday": "6",
        "comment": "test comment",
        "includedir": INSTANCE_PATH,
        "excludedir": "/tmp",
    }
    # SUCCESS
    response = client.post("/bundles/form/create", data=form_data)
    assert response.headers["BORGDRONE_RETURN"] == "BundleManager.create_bundle.SUCCESS"

    result_log = BundleManager().get_last()
    bundle = result_log.get_data()
    assert bundle

    yield bundle

    client.delete(f"/bundles/delete/{bundle.id}")


def test_get(client, logged_in):
    response = client.get("/bundles/")
    assert response.status_code == 200

    response = client.get("/bundles/form/create")
    assert response.status_code == 200


def test_check_dir(client):
    # SUCCESS
    response = client.post("/bundles/check-dir/exclude", data={"exclude_path": INSTANCE_PATH})
    assert response.headers["BORGDRONE_RETURN"] == "BundleManager.check_dir.SUCCESS"

    # FAIL
    response = client.post("/bundles/check-dir/include", data={"include_path": "/doesnotexist"})
    assert response.headers["BORGDRONE_RETURN"] == "BundleManager.check_dir.FAILURE"


def test_bundle_create(client, repository):
    form_data = {
        "repo_id": repository.id,
        "cron_minute": "2",
        "cron_hour": "3",
        "cron_day": "4",
        "cron_month": "5",
        "cron_weekday": "6",
        "comment": "test comment",
        "includedir": INSTANCE_PATH,
        "excludedir": "/tmp",
    }
    # SUCCESS
    response = client.post("/bundles/form/create", data=form_data)
    assert response.headers["BORGDRONE_RETURN"] == "BundleManager.create_bundle.SUCCESS"

    # FAIL no includedirs
    del form_data["includedir"]
    response = client.post("/bundles/form/create", data=form_data)
    assert response.headers["BORGDRONE_RETURN"] == "BundleManager.create_bundle.FAILURE"


def test_bundle_delete(client, bundle):
    response = client.delete(f"/bundles/delete/{bundle.id}")
    assert response.headers["BORGDRONE_RETURN"] == "BundleManager.delete_bundle.SUCCESS"
