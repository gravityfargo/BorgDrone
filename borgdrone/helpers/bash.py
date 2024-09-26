import subprocess
from threading import Thread

from flask import copy_current_request_context
from flask_socketio import emit

from borgdrone.extensions import socketio
from borgdrone.logging import logger


def popen(command: str | list, emit_socket: bool = False):
    if isinstance(command, str):
        cmd = command.split(" ")
    else:
        # The list constants contain list items with aguments that need to be separated
        command = " ".join(command)
        cmd = command.split(" ")
    logger.debug(cmd, "yellow")

    @copy_current_request_context  # Ensures Flask context is copied to the new thread
    def run_command():

        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as process:
            while True:
                if not process.stdout:
                    continue

                output = process.stdout.readline()
                if output:
                    line = output.strip("\n")
                    if emit_socket:
                        emit("send_line", {"text": line})
                    logger.borg_temp_log(line)
                    logger.debug(line)
                    continue

                if not process.stderr:
                    continue

                error = process.stderr.readline()
                if error:
                    line = error.strip("\n")  # Remove the newline from both sides
                    if emit_socket:
                        emit("send_line", {"text": f"{line}\n"})

                    logger.borg_temp_log(line)
                    logger.debug(line)
                    continue

                if output == "" and process.poll() is not None:
                    break

    if emit_socket:
        # Running the command in a new thread to allow Flask to continue processing other events
        socketio.start_background_task(run_command)
    else:
        thread = Thread(target=run_command)
        thread.start()


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
