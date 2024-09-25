# pylint: disable=W0611
from borgdrone.archives import Archive
from borgdrone.archives import ArchivesManager as archives_manager
from borgdrone.helpers import database
from borgdrone.logging import logger

from ..conftest import ctx_archive

# def test_get(client):
#     response = client.get("/archives/")
#     assert response.status_code == 200


# def test_get_archives(client, repository):
#     form_data = {"repo_db_id": repository.id}
#     response = client.post("/archives/get", data=form_data)
#     assert response.status_code == 200

#     response = client.post("/archives/get")
#     assert response.status_code == 200


def test_refresh_archive(client, archive):
    instance = database.get_latest(Archive)
    assert instance is not None

    archives_manager.get_one(archive_name=instance.name)
    archives_manager.get_one(db_id=instance.id)
    archives_manager.get_one(archive_id=instance.archive_id)
    archives_manager.get_all(instance.backupbundle.repo_id)

    archives_manager.refresh_archive("FakeArchive")
    result_log = archives_manager.refresh_archive(instance.name)
