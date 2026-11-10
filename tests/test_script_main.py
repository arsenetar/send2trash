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


def test_continues_after_missing_file(test_file, tmp_path):
    missing = str(tmp_path / 'does-not-exist.txt')
    with pytest.raises(SystemExit) as excinfo:
        trash_main([missing, test_file])
    assert excinfo.value.code == 1
    # the remaining file is still trashed despite the earlier failure
    assert op.exists(test_file) is False
