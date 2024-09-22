import subprocess
from typing import List

from flask import copy_current_request_context
from flask_socketio import emit

from borgdrone.extensions import socketio
from borgdrone.logging import logger as log


def popen(command: List[str]):
    @copy_current_request_context  # Ensures Flask context is copied to the new thread
    def run_command():

        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as process:
            while True:
                if not process.stdout:
                    continue

                output = process.stdout.readline()
                if output:
                    line = output.strip("\n")
                    emit("send_line", {"text": line}, broadcast=True)
                    log.borg_temp_log(line)
                    continue

                if not process.stderr:
                    continue

                error = process.stderr.readline()
                if error:
                    line = error.strip("\n")
                    emit("send_line", {"text": f"{line}\n"}, broadcast=True)
                    log.borg_temp_log(line)
                    continue

                if output == "" and process.poll() is not None:
                    # log_output("Command finished")
                    break

    # Running the command in a new thread to allow Flask to continue processing other events
    socketio.start_background_task(run_command)
    # return send_back


def run(command: str | list, capture_output=True, text_mode=True):
    if isinstance(command, str):
        cmd = command.split(" ")
    else:
        # The list constants contain list items with aguments that need to be separated
        command = " ".join(command)
        cmd = command.split(" ")

    try:
        result = subprocess.run(cmd, capture_output=capture_output, text=text_mode, check=True)
        return {"stdout": result.stdout, "returncode": int(result.returncode)}
    except subprocess.CalledProcessError as e:
        return {"stderr": e.stderr, "returncode": int(e.returncode)}
