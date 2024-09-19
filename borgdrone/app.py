import os
import secrets
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from flask import Flask, Response, render_template, request

from ._version import __version__
from .archives import archives_blueprint
from .auth import UserManager, Users, auth_blueprint
from .bundles import bundles_blueprint
from .dashboard import dashboard_blueprint
from .extensions import db, login_manager, migrate, socketio
from .helpers import ResponseHelper, filemanager
from .repositories import repositories_blueprint
from .settings import settings_blueprint


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))


def create_app(enable_logging: bool = True) -> Flask:
    config = get_secret_config()
    app = Flask(__name__)
    app.config.from_mapping(config)
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    socketio.init_app(app)

    @app.context_processor
    def utility_processor():
        return {
            "version": __version__,
        }

    @app.before_request
    def before_request():
        if request.endpoint != "static":
            hx_request = request.headers.get("HX-Request", False)
            ResponseHelper.request_method = request.method
            ResponseHelper.endpoint = request.endpoint
            ResponseHelper.hx_request = hx_request

    @app.after_request
    def render_messages(response: Response) -> Response:
        if request.headers.get("HX-Request"):
            messages = render_template("messages.html")
            response.data = response.data + messages.encode("utf-8")
        return response

    with app.app_context():
        db.create_all()
        init_db_data(app)
        app.register_blueprint(auth_blueprint, url_prefix="/auth")
        app.register_blueprint(bundles_blueprint, url_prefix="/bundles")
        app.register_blueprint(repositories_blueprint, url_prefix="/repositories")
        app.register_blueprint(archives_blueprint, url_prefix="/archives")
        app.register_blueprint(dashboard_blueprint, url_prefix="/")
        app.register_blueprint(settings_blueprint, url_prefix="/settings")

        if not enable_logging:
            # used in .logging.logger to disable debug messages during testing
            app.config["PYTESTING"] = True

        from .logging.config import configure_logging

        configure_logging()

        return app


def init_db_data(app: Flask):
    user = UserManager().get_by_id(1)
    if not user:
        user = UserManager().create(app.config["DEFAULT_USER"], app.config["DEFAULT_PASSWORD"])
        # SettingsManager().create(user_id=user.id)


def get_secret_config() -> dict[str, Any]:
    """
    A .env is only created in development mode.
    Otherwise, the environment variables are used.

    `BORGWEB_ENV` can be set to `pytest` to create a temporary instance directory
    and use a temporary database. Eventually this will be replaced with a
    better solution.

    # TODO:
    - load env vars
    - check for .env
    - create a default user if not exists with all settings
    """

    current_dir = Path(__file__).parents[1]
    instance_path = os.environ.get("INSTANCE_PATH", f"{current_dir}/instance")
    logs_dir = os.environ.get("LOGS_DIR", f"{instance_path}/logs")
    archives_log_dir = os.environ.get("ARCHIVES_LOG_DIR", f"{logs_dir}/archive_logs")
    bash_dir = os.environ.get("BASH_SCRIPTS_DIR", f"{instance_path}/bash_scripts")

    flask_env = os.environ.get("FLASK_ENV", "development")
    config_file = f"{instance_path}/borgdrone.env"

    # default config values
    config_data = {
        "SECRET_KEY": os.environ.get("SECRET_KEY", secrets.token_hex()),
        "SQLALCHEMY_TRACK_MODIFICATIONS": os.environ.get("SQLALCHEMY_TRACK_MODIFICATIONS", "False"),
        "DEFAULT_PASSWORD": os.getenv("DEFAULT_PASSWORD", "admin"),
        "DEFAULT_USER": os.getenv("DEFAULT_USER", "admin"),
        "INSTANCE_PATH": instance_path,
        "LOGS_DIR": logs_dir,
        "ARCHIVES_LOG_DIR": archives_log_dir,
        "BASH_SCRIPTS_DIR": bash_dir,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{instance_path}/borgdrone.sqlite3",
        "FLASK_RUN_PORT": os.environ.get("FLASK_RUN_PORT", "5000"),
        "FLASK_DEBUG": os.environ.get("FLASK_DEBUG", "True"),
        "FLASK_APP": "borgdrone",
        "SESSION_COOKIE_SAMESITE=": "Lax",
    }

    # check instance directories

    filemanager.check_dir(instance_path, create=True)
    filemanager.check_dir(logs_dir, create=True)
    filemanager.check_dir(archives_log_dir, create=True)
    filemanager.check_dir(bash_dir, create=True)

    # create the .env file if in development mode
    if flask_env == "development":
        result = filemanager.check_file(config_file)
        if not result:
            try:
                with open(config_file, "w", encoding="utf-8") as f:
                    for key, value in config_data.items():
                        f.write(f"{key}={value}\n")
            except Exception as e:
                raise e
        config_data = dotenv_values(config_file)

    for key, value in config_data.items():
        if key.startswith("FLASK_"):
            if value:
                os.environ[key] = value

    return config_data
