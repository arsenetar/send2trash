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


@pytest.mark.parametrize("continue_on_error", [False, True])
def test_batch_success(monkeypatch, capsys, continue_on_error):
    calls = []
    monkeypatch.setattr("send2trash.__main__.send2trash", calls.append)
    args = ["-v", "first", "second"]
    if continue_on_error:
        args.insert(0, "--continue-on-error")

    trash_main(args)

    assert calls == ["first", "second"]
    captured = capsys.readouterr()
    assert captured.out == "Trashed «first»\nTrashed «second»\n"
    assert captured.err == ""


@pytest.mark.parametrize("continue_on_error", [False, True])
@pytest.mark.parametrize("failed_files", [("first",), ("second",), ("first", "second")])
def test_batch_errors(monkeypatch, capsys, continue_on_error, failed_files):
    calls = []

    def trash(filename):
        calls.append(filename)
        if filename in failed_files:
            raise OSError("Cannot trash " + filename)

    monkeypatch.setattr("send2trash.__main__.send2trash", trash)
    files = ["first", "second", "third"]
    args = ["-v"] + files
    if continue_on_error:
        args.insert(0, "--continue-on-error")

    with pytest.raises(SystemExit) as exc:
        trash_main(args)

    assert exc.value.code == 1
    expected_calls = files if continue_on_error else files[:files.index(failed_files[0]) + 1]
    assert calls == expected_calls
    captured = capsys.readouterr()
    assert captured.out == "".join("Trashed «" + name + "»\n" for name in calls if name not in failed_files)
    assert captured.err == "".join("Cannot trash " + name + "\n" for name in calls if name in failed_files)


def test_continue_on_error_does_not_hide_unexpected_errors(monkeypatch):
    def trash(filename):
        raise RuntimeError("unexpected error")

    monkeypatch.setattr("send2trash.__main__.send2trash", trash)

    with pytest.raises(RuntimeError, match="unexpected error"):
        trash_main(["--continue-on-error", "first"])
