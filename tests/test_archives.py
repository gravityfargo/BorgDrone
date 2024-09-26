from flask.testing import FlaskClient

from borgdrone.archives import Archive
from borgdrone.archives import ArchivesManager as archives_manager
from borgdrone.borg import BorgRunner as borg_runner
from borgdrone.bundles import BackupBundle, BackupDirectory
from borgdrone.helpers import bash, database, datahelpers, filemanager
from borgdrone.logging import logger
from borgdrone.repositories import Repository


def test_get(client: FlaskClient, archive: Archive):
    response = client.get("/archives/")
    assert response.status_code == 200

    repository = database.get_latest(Repository)
    assert repository

    archives_manager.get_one(archive_name=archive.name)
    archives_manager.get_one(db_id=archive.id)
    archives_manager.get_one(archive_id=archive.archive_id)
    archives_manager.get_all(repository.id)


def test_get_archives(client: FlaskClient):
    repository = database.get_latest(Repository)
    assert repository

    form_data = {"repo_db_id": repository.id}
    response = client.post("/archives/get", data=form_data)
    assert response.status_code == 200

    response = client.post("/archives/get")
    assert response.status_code == 200


def test_refresh_archive(client: FlaskClient, archive: Archive):

    result_log = archives_manager.refresh_archive("FakeArchive")
    assert result_log.status == "FAILURE"

    result_log = archives_manager.refresh_archive(archive.name)
    assert result_log.status == "SUCCESS"


def test_import_archives(client: FlaskClient):
    repository = database.get_latest(Repository)
    assert repository

    name = "{hostname}-{user}-{now:%Y-%m-%dT%H:%M:%S.%f}"
    commands = [
        f"borg create --list --no-cache-sync --exclude /tmp/borgdrone_pytest/data/exclude2 {repository.path}::{name} /tmp/borgdrone_pytest/data/include1 /tmp/borgdrone_pytest/data/include2",
        f"borg create --stats --exclude /tmp/borgdrone_pytest/data/exclude1 {repository.path}::{name} /tmp/borgdrone_pytest/data/include2",
        f"borg create --progress {repository.path}::{name} /tmp/borgdrone_pytest/data/include1",
        f"borg create --progress {repository.path}::{name} /tmp/borgdrone_pytest/data/include1",
    ]
    # create 4 archives
    for i, command in enumerate(commands):
        logger.debug(f"Creating archive {i+1}", "yellow")
        bash.run(command)

    assert database.count(BackupBundle) == 1

    result_log = archives_manager.import_archives(repository)

    assert result_log.status == "SUCCESS"
    assert database.count(Archive) == 4
    assert database.count(BackupBundle) == 4
    assert database.count(BackupDirectory) == 4

    # cleanup the new bundles
    for i in range(3):
        bundle = database.get_latest(BackupBundle)
        assert bundle
        bundle.delete()

    assert database.count(BackupBundle) == 1


# archives_manager.
