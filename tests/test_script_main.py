# encoding: utf-8
import os
import sys
import pytest
from tempfile import NamedTemporaryFile
from os import path as op

from send2trash.__main__ import main as trash_main

# Only import HOMETRASH on supported platforms
if sys.platform != "win32":
    from send2trash.plat_other import HOMETRASH


@pytest.fixture
def file():
    file = NamedTemporaryFile(dir=op.expanduser("~"), prefix="send2trash_test", delete=False)
    file.close()
    # Verify file was actually created
    assert op.exists(file.name) is True
    yield file.name
    # Cleanup trash files on supported platforms
    if sys.platform != "win32":
        name = op.basename(file.name)
        # Remove trash files if they exist
        if op.exists(op.join(HOMETRASH, "files", name)):
            os.remove(op.join(HOMETRASH, "files", name))
            os.remove(op.join(HOMETRASH, "info", name + ".trashinfo"))
    if op.exists(file.name):
        os.remove(file.name)


def test_trash(file):
    trash_main(["-v", file])
    assert op.exists(file) is False


def test_no_args(file):
    pytest.raises(SystemExit, trash_main, [])
    pytest.raises(SystemExit, trash_main, ["-v"])
    assert op.exists(file) is True
