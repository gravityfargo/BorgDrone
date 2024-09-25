from sqlalchemy import select

from borgdrone.extensions import db
from borgdrone.types import OptInt, OptStr

from .models import BackupDirectory, OptBackupDirectory


def get_one(bundledirectory_id: OptInt = None, path: OptStr = None) -> OptBackupDirectory:
    stmt = None
    instance = None

    if bundledirectory_id:
        stmt = select(BackupDirectory).where(BackupDirectory.id == bundledirectory_id)
    elif path:
        stmt = select(BackupDirectory).where(BackupDirectory.path == path)

    if stmt is not None:
        instance = db.session.scalars(stmt).first()

    return instance


def create_bundledirectory(**kwargs) -> BackupDirectory:
    # Create a new BackupDirectory instance
    backupdirectory = BackupDirectory()
    backupdirectory.path = kwargs["path"]
    backupdirectory.permissions = kwargs["permissions"]
    backupdirectory.owner = kwargs["owner"]
    backupdirectory.group = kwargs["group"]
    backupdirectory.exclude = kwargs["exclude"]
    backupdirectory.commit()

    return backupdirectory


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
