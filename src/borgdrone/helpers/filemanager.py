import os


def check_dir(dir_path: str, create: bool = False) -> bool:
    """
    Check/create a directory.
    True: Directory exists
    False: Directory does not exist and was not created
    """
    if not os.path.exists(dir_path):
        if create:
            create_dir(dir_path)
            return True

        return False
    return True


def check_file(file_path: str, create: bool = False) -> bool:
    """
    Check if a file exists. If it does not exist, create it or raise FileNotFoundError.

    return True if the file exists, False if it was created
    """
    if not os.path.exists(file_path):
        if create:
            create_file(file_path)
            return True

        return False
    return True


def create_file(file_path: str) -> None:
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            file.write("")
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Error Creating {file_path}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error occurred while creating {file_path}") from e


def create_dir(dir_path: str) -> None:
    """Create a directory."""
    try:
        os.makedirs(dir_path)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Error Creating {dir_path}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error occurred while creating {dir_path}") from e


def get_directories(dir_path: str) -> list:
    """Get a list of directories in a directory."""
    dirs = []
    for item in os.listdir(dir_path):
        if os.path.isdir(os.path.join(dir_path, item)):
            dirs.append(item)
    return dirs


def process_line(line: str):
    """Process a line from the tree command."""
    line_copy2 = line.rstrip().split(" ")

    if len(line_copy2) == 1:
        return
    if line_copy2[0].isdigit():
        print("Summary Line")
        return

    bytes_str = ""
    for i in line:
        if i == "[":
            continue
        if i.isdigit():
            bytes_str = bytes_str + i
            continue
        if i == "]":
            break

    dir_level = 0
    for i in line_copy2:
        if i != "":
            break
        dir_level += 1

    dir_level = dir_level // 4
    return [dir_level, int(bytes_str)]
