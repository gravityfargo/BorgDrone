import os

import pytest
from flask_login import current_user

from borgdrone.bundles import BundleManager
from borgdrone.helpers import filemanager
from borgdrone.repositories import RepositoryManager

from ..conftest import INSTANCE_PATH, new_instance_subdir
from .test_repositories import test_repo


def bundle_dir_data(client, dir_path: str):
    test_path = os.path.join(INSTANCE_PATH, dir_path)
    response = client.post("/bundles/check-dir/include", data={"include_path": test_path})
    dir_data = response.data.splitlines()

    test_path_data = f"""
        {dir_data[3].decode("utf-8").strip()}
        {dir_data[4].decode("utf-8").strip()}
        {dir_data[5].decode("utf-8").strip()}
        {dir_data[6].decode("utf-8").strip()}
    """

    form_data = {
        "cron_minute": "2",
        "cron_hour": "3",
        "cron_day": "4",
        "cron_month": "5",
        "cron_weekday": "6",
        "comment": "test comment",
        "includedir": test_path_data,
        "excludedir": test_path_data,
    }
    return form_data


@pytest.fixture(scope="function", name="bundle")
def test_bundle(client, repository):
    sub_dir = new_instance_subdir()
    dir_data = bundle_dir_data(client, sub_dir)

    # SUCCESS
    dir_data["repo_id"] = repository.id
    response = client.post("/bundles/form/create", data=dir_data)
    assert response.headers["BORGDRONE_RETURN"] == "BundleManager.create_bundle.SUCCESS"

    result_log = BundleManager().get_last()
    bundle = result_log.get_data()
    assert bundle

    return bundle


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


def test_bundle_create_fail(client, repository):
    # FAIL no includedirs
    sub_dir = new_instance_subdir()
    dir_data = bundle_dir_data(client, sub_dir)
    dir_data["repo_id"] = repository.id
    del dir_data["includedir"]

    response = client.post("/bundles/form/create", data=dir_data)
    assert response.headers["BORGDRONE_RETURN"] == "BundleManager.create_bundle.FAILURE"


def test_bundle_delete(client, bundle):
    response = client.delete(f"/bundles/delete/{bundle.id}")
    assert response.headers["BORGDRONE_RETURN"] == "BundleManager.delete_bundle.SUCCESS"
