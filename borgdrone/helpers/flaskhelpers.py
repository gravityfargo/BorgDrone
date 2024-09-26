from typing import Any

from flask import Response
from flask import current_app as app
from flask import (
    flash,
    make_response,
    redirect,
    render_template,
    render_template_string,
    url_for,
)

# from borgdrone.logging import BorgdroneEvent
from borgdrone.logging import logger as log

JINJA_TEMPLATE = """
{% extends 'base.html' %}
{% block content %}
<script>
    select_tab("{{ selected_tab }}");
</script>

{% include 'TEMPLATE_FRAGMENT' %}

{% endblock content %}
"""


class ResponseHelper:
    # both class variables are set in the before_request hook
    endpoint: str = ""
    hx_request: bool = False
    request_method: str = ""

    def __init__(self, **kwargs: Any):
        self.get_template: str = kwargs.get("get_template", "")
        self.get_error_template: str = kwargs.get("get_error_template", "")
        self.post_success_template: str = kwargs.get("post_success_template", "")
        self.post_error_template: str = kwargs.get("post_error_template", "")

        self.returncode: int = kwargs.get("returncode", 200)
        self.borgdrone_return: str = kwargs.get("borgdrone_return", "")

        self.htmx_refresh: bool = kwargs.get("htmx_refresh", False)

        self.toast_success: str = kwargs.get("toast_success", "")
        self.toast_error: str = kwargs.get("toast_error", "")
        self.toast_info: str = kwargs.get("toast_info", "")
        self.toast_warning: str = kwargs.get("toast_warning", "")

        self.headers: dict = kwargs.get("headers", {})
        self.context_data: dict = kwargs.get("context_data", {})

        # self.borgdrone_event: Optional[BorgdroneEvent] = None

    def respond(self, redirect_url: str = "", error: bool = False, empty: bool = False, data: str = "") -> Response:
        base_name = self.endpoint.split(".")[0]
        self.context_data["selected_tab"] = f"{base_name}_tab"

        response = self._respond_empty()

        if redirect_url:
            response = self.respond_redirect(redirect_url)

        elif empty:
            response = self._respond_empty()

        elif data:
            response = self.respond_data(data)

        else:
            match self.request_method:
                case "GET":
                    if error:
                        template = self.get_error_template
                    else:
                        template = self.get_template

                    if self.hx_request:
                        response = self.respond_template(template)
                    else:
                        response = self.__respond_jinja(template)

                case "POST":
                    if error:
                        template = self.post_error_template
                    else:
                        template = self.post_success_template

                    if error and not template:
                        response = self._respond_empty()

                    elif self.hx_request:
                        response = self.respond_template(template)

                    else:
                        response = self.__respond_jinja(template)

                case "DELETE":
                    response = self._respond_empty()

        self.__log()
        self.__toast()
        self.__headers(response)
        return response

    def __log(self) -> None:
        hx = ""

        endpoint = self.endpoint
        if self.hx_request:
            hx = "HX-Request"
            endpoint = f"{self.endpoint} ({hx})"
        message = f"[ {self.request_method} :: {endpoint:<20} ]"

        if app.config["PYTESTING"] == "False":
            log.debug(message)

    def __toast(self) -> None:
        if self.toast_success:
            level = "SUCCESS"
            message = self.toast_success

        elif self.toast_error:
            level = "ERROR"
            message = self.toast_error

        elif self.toast_info:
            level = "INFO"
            message = self.toast_info

        elif self.toast_warning:
            level = "WARNING"
            message = self.toast_warning

        else:
            return

        flash(message, level)

    def __headers(self, response: Response) -> None:
        for key, value in self.headers.items():
            response.headers[key] = value

        if self.htmx_refresh:
            response.headers["HX-Refresh"] = "true"

        if self.borgdrone_return:
            response.headers["BORGDRONE_RETURN"] = self.borgdrone_return

    def respond_template(self, template: str) -> Response:
        response = make_response(render_template(template, **self.context_data), self.returncode)
        return response

    def respond_redirect(self, target) -> Response:
        if self.returncode == 200:
            self.returncode = 302

        response = make_response(redirect(url_for(target, **self.context_data)), self.returncode)
        return response

    def respond_data(self, data: str = "") -> Response:
        response = make_response(data, self.returncode)
        return response

    def _respond_empty(self) -> Response:
        response = make_response()
        return response

    def __respond_jinja(self, template: str) -> Response:
        template = JINJA_TEMPLATE.replace("TEMPLATE_FRAGMENT", template)
        data = render_template_string(template, **self.context_data)

        response = make_response(data)
        return response
