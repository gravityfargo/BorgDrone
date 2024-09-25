from time import sleep

from borgdrone.archives import Archive
from borgdrone.archives import ArchivesManager as archives_manager
from borgdrone.borg import BorgRunner as borg_runnder
from borgdrone.bundles import BackupBundle, BackupDirectory
from borgdrone.helpers import bash, database, datahelpers, filemanager
from borgdrone.logging import logger

from .conftest import ctx_archive, ctx_bundle

# def test_get(client, archive):
#     response = client.get("/archives/")
#     assert response.status_code == 200

#     instance = database.get_latest(Archive)
#     assert instance
#     archives_manager.get_one(archive_name=instance.name)
#     archives_manager.get_one(db_id=instance.id)
#     archives_manager.get_one(archive_id=instance.archive_id)
#     archives_manager.get_all(instance.backupbundle.repo_id)


# def test_get_archives(client, repository):
#     form_data = {"repo_db_id": repository.id}
#     response = client.post("/archives/get", data=form_data)
#     assert response.status_code == 200

#     response = client.post("/archives/get")
#     assert response.status_code == 200


# def test_refresh_archive(client, archive):
#     instance = database.get_latest(Archive)
#     assert instance

#     archives_manager.refresh_archive("FakeArchive")
#     result_log = archives_manager.refresh_archive(instance.name)


def test_sync_archives_with_db(app):
    pass


# bundle_instance = database.get_latest(BackupBundle)
# assert bundle_instance
# assert bundle_instance.command_line

# # create 4 archives
# for _ in range(4):
#     logger.error(_)
#     bash.popen(bundle_instance.command_line)
#     sleep(0.75)

# archives_manager.
