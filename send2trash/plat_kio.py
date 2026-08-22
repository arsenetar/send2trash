# Copyright 2026 Hardcoded Software (http://www.hardcoded.net)

# This software is licensed under the "BSD" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.hardcoded.net/licenses/bsd_license

import os
import shutil
import subprocess
from functools import lru_cache
from urllib.parse import quote

from send2trash.util import preprocess_paths


@lru_cache(maxsize=1)
def _kioclient():
    for name in ("kioclient6", "kioclient5", "kioclient"):
        command = shutil.which(name)
        if command is not None:
            return command
    raise ImportError("No kioclient executable found")


def _is_kde_session():
    if os.environ.get("KDE_FULL_SESSION", "").lower() == "true":
        return True

    desktop_values = " ".join(
        os.environ.get(name, "") for name in (
            "XDG_CURRENT_DESKTOP", 
            "XDG_SESSION_DESKTOP", 
            "DESKTOP_SESSION"
        )
    ).lower()
    return "kde" in desktop_values or "plasma" in desktop_values


def _path_to_url(path):
    # KIO expects local file URLs rather than raw filesystem paths.
    return "file://" + quote(os.path.abspath(os.fsdecode(path)))


def is_available():
    if not _is_kde_session():
        return False

    try:
        command = _kioclient()
    except ImportError:
        return False

    try:
        result = subprocess.run(
            [
                command, "stat", "trash:/"
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
            check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def send2trash(paths):
    paths = preprocess_paths(paths)
    command = [_kioclient(), "move", *(_path_to_url(path) for path in paths), "trash:/"]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as error:
        message = error.stderr.strip() \
            or error.stdout.strip() \
            or f"{command[0]} exited with status {error.returncode}"
        raise OSError(message) from error
