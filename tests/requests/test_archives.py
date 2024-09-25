import pytest

from borgdrone.bundles import BundleManager as bundle_manager
from borgdrone.logging import logger as log

import tests.conftest


@pytest.fixture(scope="session", name="archive")
def test_BundleManager_create_backup(logged_in, repository, bundle):
    result_log = bundle_manager.create_backup(bundle.id)
    assert result_log.status == "SUCCESS"
    return result_log.data


def test_get(client, logged_in, archive):
    response = client.get("/archives/")
    assert response.status_code == 200


def test_get_archives(client, logged_in, repository):
    form_data = {"repo_db_id": repository.id}
    response = client.post("/archives/get", data=form_data)
    log.warning(response.headers["BORGDRONE_RETURN"])

    assert response.status_code == 200
