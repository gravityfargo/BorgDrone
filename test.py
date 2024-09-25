command_line = "borg --show-version create --stats --progress --one-file-system --exclude /home/nathan/Documents --exclude /home/nathan/Desktop /tmp/borgdrone::{hostname}-{user}-{now} /home/nathan/Downloads"

#    borg
# --show-version
# create
# --stats
# --progress
# --one-file-system
# --exclude /home/nathan/Documents
# --exclude /home/nathan/Desktop
# /tmp/borgdrone::{hostname}-{user}-{now}
# /home/nathan/Downloads /home/nathan/Music

# result_log = repository_manager.get_one(db_id=repo_db_id)
# if not (repository := result_log.get_data()):
#     return _log.not_found_message("Repository")
