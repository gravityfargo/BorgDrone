from flask import Flask, Response, render_template, request

from ._version import __version__
from .archives import archives_blueprint
from .auth import UserManager as user_manager
from .auth import Users, auth_blueprint
from .bundles import bundles_blueprint
from .dashboard import dashboard_blueprint
from .extensions import db, login_manager, migrate, socketio
from .helpers import ResponseHelper, bash
from .repositories import repositories_blueprint
from .settings import environ, settings_blueprint


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))


def create_app() -> Flask:
    """
    Flow:
    - User makes a request with browser refresh, or htmx/form POST/DELETE etc
    - @app.before_request
        - sets ResponseHelper class variables
    - ResponseHelper processes the request, and forms the requested response
    - @app.context_processor
        - adds gloabl variables to the template context
    - response is returned to the user
    - @app.after_request
        - renders toast messages if hx-request is present to avoid a page reload
    """
    app = Flask(__name__)
    config_data = environ.load_config()
    app.config.from_mapping(config_data)

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
            """
            this sets class variables for the ResponseHelper
            using this information, the ResponseHelper can determine
            which template to load (get, post_success, post_failure)
            and if it should load the template fragment, or the full page
            with Flask.render_template_string
            """
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

    bash.run("echo 'Borgdrone is running!'")

    with app.app_context():

        db.create_all()
        init_db_data(app)
        app.register_blueprint(auth_blueprint, url_prefix="/auth")
        app.register_blueprint(bundles_blueprint, url_prefix="/bundles")
        app.register_blueprint(repositories_blueprint, url_prefix="/repositories")
        app.register_blueprint(archives_blueprint, url_prefix="/archives")
        app.register_blueprint(dashboard_blueprint, url_prefix="/")
        app.register_blueprint(settings_blueprint, url_prefix="/settings")

        from .logging.config import configure_logging

        configure_logging()

        return app


def init_db_data(app: Flask):
    result_log = user_manager.get_one(user_id=1)

    if not result_log.get_data():
        user_manager.create(app.config["DEFAULT_USER"], app.config["DEFAULT_PASSWORD"])
        # SettingsManager().create(user_id=user.id)
