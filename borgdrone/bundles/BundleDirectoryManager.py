from sqlalchemy import select

from borgdrone.extensions import db
from borgdrone.logging import BorgdroneEvent
from borgdrone.types import OptInt

from .models import BackupBundle, BackupDirectory, OptBackupBundle, OptBackupDirectory


def get_one(bundle: OptBackupBundle = None, bundledirectory_id: OptInt = None) -> BorgdroneEvent[OptBackupDirectory]:

    _log = BorgdroneEvent[OptBackupDirectory]()
    _log.event = "BundleManager.get_one"

    instance = None

    if bundle:
        stmt = select(BackupDirectory).join(BackupDirectory.backupbundles).where(BackupBundle.id == bundle.id)
        instance = db.session.scalars(stmt).first()

    _log.set_data(instance)

    if not instance:
        _log.status = "FAILURE"
        _log.error_message = "BackupDirectory not found."
    else:
        _log.status = "SUCCESS"
        _log.message = "BackupDirectory Retrieved."

    return _log


def create_bundledirectory(**kwargs) -> BorgdroneEvent[OptBackupDirectory]:
    _log = BorgdroneEvent[OptBackupDirectory]()
    _log.event = "BundleDirectoryManager.create_bundledirectory"

    # # Check if a BackupDirectory with the same attributes already exists
    # existing_directory = db.session.scalars(
    #     select(BackupDirectory)
    #     .where(BackupDirectory.path == kwargs["path"])
    #     .where(BackupDirectory.permissions == kwargs["permissions"])
    #     .where(BackupDirectory.owner == kwargs["owner"])
    #     .where(BackupDirectory.group == kwargs["group"])
    # ).first()

    # if existing_directory:
    #     _log.set_data(existing_directory)
    #     return _log.return_failure("Duplicate Backup Directory exists.")

    # # Create a new BackupDirectory if no duplicate is found
    # backup_directory = BackupDirectory(
    #     path=kwargs["path"],
    #     permissions=kwargs["permissions"],
    #     owner=kwargs["owner"],
    #     group=kwargs["group"],
    #     exclude=kwargs.get("exclude", False),
    # )

    # db.session.add(backup_directory)
    # db.session.commit()

    # _log.set_data(backup_directory)
    return _log.return_success("Backup Directory created successfully.")
