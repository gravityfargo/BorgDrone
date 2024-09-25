from sqlalchemy import select

from borgdrone.extensions import db
from borgdrone.logging import BorgdroneEvent
from borgdrone.types import OptBool, OptInt, OptStr

from .models import BackupBundle, BackupDirectory, OptBackupDirectory


def get_one(bundledirectory_id: OptInt = None, path: OptStr = None) -> BorgdroneEvent[OptBackupDirectory]:
    _log = BorgdroneEvent[OptBackupDirectory]()
    _log.event = "BundleManager.get_one"

    instance = None

    if bundledirectory_id:
        stmt = select(BackupDirectory).where(BackupDirectory.id == bundledirectory_id)
        instance = db.session.scalars(stmt).first()
    elif path:
        stmt = select(BackupDirectory).where(BackupDirectory.path == path)
        instance = db.session.scalars(stmt).first()

    _log.set_data(instance)

    if not instance:
        _log.status = "FAILURE"
        _log.error_message = "BackupDirectory not found."
    else:
        _log.status = "SUCCESS"
        _log.message = "BackupDirectory Retrieved."

    return _log


def find_exact_match(**kwargs) -> BorgdroneEvent[OptBackupDirectory]:
    _log = BorgdroneEvent[OptBackupDirectory]()
    _log.event = "BundleDirectoryManager.find_exact_match"

    stmt = (
        select(BackupDirectory)
        .where(BackupDirectory.path == kwargs["path"])
        .where(BackupDirectory.permissions == kwargs["permissions"])
        .where(BackupDirectory.owner == kwargs["owner"])
        .where(BackupDirectory.group == kwargs["group"])
        .where(BackupDirectory.exclude == kwargs.get("exclude", False))
    )
    match = db.session.scalars(stmt).first()

    _log.set_data(match)

    if not match:
        _log.error_message = "BackupDirectory not in database."
    else:
        _log.message = "BackupDirectory Retrieved."

    return _log


def get_or_create_bundledirectory(
    bundle: BackupBundle, update: OptBool = None, **kwargs
) -> BorgdroneEvent[OptBackupDirectory]:
    _event = "BundleDirectoryManager.get_or_create_bundledirectory"

    # Attempt to find an exact match to avoid duplication
    result_log = find_exact_match(**kwargs)
    result_log.event = _event

    if result_log.status == "SUCCESS":
        # BackupDirectory already exists, no need to create a new one

        if update and result_log.data:
            # Update if requested
            result_log.data.update(**kwargs)
            return result_log.return_success("Backup Directory found and updated.")

        # Attach the existing BackupDirectory to the bundle if not already attached
        if backup_dir := result_log.get_data():
            if backup_dir not in bundle.backupdirectories:
                bundle.backupdirectories.append(backup_dir)
                bundle.commit()  # Commit the association
                return result_log.return_success("Backup Directory found and attached to bundle.")

    # If no match was found, create a new one
    result_log = create_bundledirectory(bundle, **kwargs)
    result_log.event = _event

    if result_log.status == "SUCCESS":
        return result_log.return_success("Backup Directory created.")
    else:
        return result_log.return_failure("Backup Directory could not be created.")


def create_bundledirectory(bundle: BackupBundle, **kwargs) -> BorgdroneEvent[OptBackupDirectory]:
    _log = BorgdroneEvent[OptBackupDirectory]()
    _log.event = "BundleDirectoryManager.create_bundledirectory"

    # Create a new BackupDirectory instance
    backupdirectory = BackupDirectory()
    backupdirectory.path = kwargs["path"]
    backupdirectory.permissions = kwargs["permissions"]
    backupdirectory.owner = kwargs["owner"]
    backupdirectory.group = kwargs["group"]
    backupdirectory.exclude = kwargs["exclude"]
    backupdirectory.commit()

    _log.set_data(backupdirectory)

    if not backupdirectory:
        _log.status = "FAILURE"
        _log.error_message = "BackupDirectory could not be created."
    else:
        _log.status = "SUCCESS"
        _log.message = "BackupDirectory created successfully."

    return _log


# def update_bundledirectory(bundle: BackupBundle, **kwargs) -> BorgdroneEvent[OptBackupDirectory]:
#     _log = BorgdroneEvent[OptBackupDirectory]()
#     _log.event = "BundleDirectoryManager.update_bundledirectory"

# # Check if the BackupDirectory exists
# existing_directory = db.session.scalars(select(BackupDirectory).where(BackupDirectory.id == bundledirectory_id)).first()

# if not existing_directory:
#     return _log.return_failure("Backup Directory not found.")

# # Update the BackupDirectory
# stmt = (
#     update(BackupDirectory)
#     .where(BackupDirectory.id == bundled
