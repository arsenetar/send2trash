from os import path as op
import pytest

from send2trash.__main__ import main as trash_main


def test_trash(test_file):
    trash_main(["-v", test_file])
    assert op.exists(test_file) is False


def test_no_args(test_file):
    pytest.raises(SystemExit, trash_main, [])
    pytest.raises(SystemExit, trash_main, ["-v"])
    assert op.exists(test_file) is True
