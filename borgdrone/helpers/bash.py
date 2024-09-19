import subprocess
from typing import List

from flask import copy_current_request_context
from flask_socketio import emit

from borgdrone.extensions import socketio
from borgdrone.logging import logger as log


def popen(command: List[str], logger: str = "") -> str:
    send_back = ""

    @copy_current_request_context  # Ensures Flask context is copied to the new thread
    def run_command():

        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as process:

            def log_output(line: str):
                nonlocal send_back
                if logger == "borg_create_log":
                    log.borg_create_log(line)
                    if "Archive name: " in line:
                        send_back = line
                        print(send_back)
                log.debug(line)

            while True:
                if not process.stdout:
                    continue

                output = process.stdout.readline()
                if output:
                    line = output.strip()
                    log_output(line)
                    emit("send_line", {"line": line}, broadcast=True)
                    continue

                if not process.stderr:
                    continue

                error = process.stderr.readline()
                if error:
                    line = error.strip()
                    log_output(line)
                    emit("send_line", {"line": f"{line}\n"}, broadcast=True)
                    continue

                if output == "" and process.poll() is not None:
                    log_output("Command finished")
                    break

    # Running the command in a new thread to allow Flask to continue processing other events
    socketio.start_background_task(run_command)
    return send_back


def run(command: str | list, capture_output=True, text_mode=True):
    if isinstance(command, str):
        cmd = command.split(" ")
    else:
        cmd = command
    try:
        result = subprocess.run(cmd, capture_output=capture_output, text=text_mode, check=True)
        return {"stdout": result.stdout, "returncode": int(result.returncode)}
    except subprocess.CalledProcessError as e:
        return {"stderr": e.stderr, "returncode": int(e.returncode)}
