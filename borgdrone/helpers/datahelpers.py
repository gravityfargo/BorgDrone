import hashlib
from datetime import datetime


def hash_data(data) -> str:
    """Hash data using SHA-256.

    Used to easily compare data.
    """
    data_bytes = str(data).encode("utf-8")
    return hashlib.sha256(data_bytes).hexdigest()


def convert_bytes(size_in_bytes: int, base: int = 1000) -> str:
    """Convert bytes to a human-readable string format (KB, MB, GB, etc.) using 1000 as the conversion base."""
    units = ["B ", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
    size = size_in_bytes
    unit_index = 0

    while size >= base and unit_index < len(units) - 1:
        size /= base
        unit_index += 1

    return f"{size:.2f} {units[unit_index]}"


def convert_rwx_to_octal(rwx: str) -> str:
    """Convert a string representation of file permissions (rwx) to an octal representation."""
    rwx_in = [rwx[1:4], rwx[4:7], rwx[7:]]
    result = ""
    octal = 0
    for i in rwx_in:
        for c in i:
            if c == "r":
                octal += 4
            elif c == "w":
                octal += 2
            elif c == "x":
                octal += 1
        result += str(octal)
        octal = 0
    return result


def ISO8601_to_human(iso_date_str: str) -> str:
    """
    Convert an  date string to a human-readable format like 'Saturday, September 14, 2024'.

    :param iso_date_str: ISO 8601 formatted date string
    :return: Human-readable formatted date string
    """
    # Parse the ISO date string
    date_obj = datetime.fromisoformat(iso_date_str)

    # Convert to human-readable format
    return date_obj.strftime("%Y/%m/%d at %H:%M:%S")
