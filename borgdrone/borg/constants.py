# Base commands
BORG_CHECK_COMMAND = [
    "borg --log-json check",
]

BORG_INIT_COMMAND = "borg --log-json init --encryption=KEY PATH"


BORG_INFO_COMMAND = [
    "borg --log-json info --json",
    "PATH",
]

BORG_DELETE_COMMAND = [
    "borg --log-json delete --force",
    "PATH",
]

BORG_CREATE_COMMAND = [
    "borg",
    "create",
    "--list --stats --progress --one-file-system",
]
# --exclude /dir/to/exclude
# PATH::NAME_FORMAT
# /dir/to/include

BORG_LIST_COMMAND = [
    "borg --log-json list --json",
    "PATH",
    "--format '{archive}{name}{id}{tam}{start}{time}{end}{command_line}{hostname}{username}'",
]
