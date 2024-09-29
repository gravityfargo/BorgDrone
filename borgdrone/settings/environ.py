import os
import secrets
from pathlib import Path
from typing import Any, Dict

from dotenv import dotenv_values

from borgdrone.helpers import filemanager


def load_env_file(instance_path: str, config_path: str) -> Dict[str, str | None]:
    user_config = {
        "SECRET_KEY": os.environ.get("SECRET_KEY", secrets.token_hex()),
        "DEFAULT_PASSWORD": os.getenv("DEFAULT_PASSWORD", "admin"),
        "DEFAULT_USER": os.getenv("DEFAULT_USER", "admin"),
        "INSTANCE_PATH": instance_path,
        "FLASK_RUN_PORT": os.environ.get("FLASK_RUN_PORT", "5000"),
    }

    result = filemanager.check_file(config_path)
    if not result:
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                for key, value in user_config.items():
                    f.write(f"{key}={value}\n")

        except Exception as e:
            raise e

    return dotenv_values(config_path)


def load_config() -> dict[str, Any]:
    # Instance Path
    current_dir = Path(__file__).parents[2]
    instance_path = os.environ.get("INSTANCE_PATH", f"{current_dir}/instance")

    # Subdirectories
    logs_dir = os.environ.get("LOGS_DIR", f"{instance_path}/logs")
    archives_log_dir = os.environ.get("ARCHIVES_LOG_DIR", f"{logs_dir}/archive_logs")
    bash_dir = os.environ.get("BASH_SCRIPTS_DIR", f"{instance_path}/bash_scripts")

    # check instance directories
    filemanager.check_dir(instance_path, create=True)
    filemanager.check_dir(logs_dir, create=True)
    filemanager.check_dir(archives_log_dir, create=True)
    filemanager.check_dir(bash_dir, create=True)

    config_sqlalchemy = {
        "SQLALCHEMY_TRACK_MODIFICATIONS": os.environ.get("SQLALCHEMY_TRACK_MODIFICATIONS", "False"),
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{instance_path}/borgdrone.sqlite3",
    }

    config_flask = {
        "FLASK_DEBUG": os.environ.get("FLASK_DEBUG", "True"),
        "FLASK_ENV": os.environ.get("FLASK_ENV", "development"),
        "FLASK_APP": "borgdrone",
        "TEMPLATES_AUTO_RELOAD": "True",
    }
    config_borgdrone = {
        "PYTESTING": os.environ.get("PYTESTING", "False"),
        "LOGS_DIR": logs_dir,
        "ARCHIVES_LOG_DIR": archives_log_dir,
        "BASH_SCRIPTS_DIR": bash_dir,
    }

    config_file_path = f"{instance_path}/borgdrone.env"
    config_data = load_env_file(instance_path, config_file_path)

    config_data.update(config_sqlalchemy)
    config_data.update(config_flask)
    config_data.update(config_borgdrone)

    for key, value in config_data.items():
        if key and value:
            os.environ[key] = value

    return config_data
