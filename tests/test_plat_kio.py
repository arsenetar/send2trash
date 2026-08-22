import subprocess

import pytest

import send2trash.plat_kio as plat_kio


def test_kioclient_prefers_newest_available(monkeypatch):
    def fake_which(name):
        return {
            "kioclient6": None,
            "kioclient5": "/usr/bin/kioclient5",
            "kioclient": "/usr/bin/kioclient",
        }[name]

    monkeypatch.setattr(plat_kio.shutil, "which", fake_which)
    assert plat_kio._kioclient() == "/usr/bin/kioclient5"


def test_is_kde_session_detects_kde_env(monkeypatch):
    monkeypatch.setattr(
        plat_kio.os,
        "environ",
        {
            "KDE_FULL_SESSION": "true",
        },
        raising=False,
    )
    assert plat_kio._is_kde_session() is True


def test_is_kde_session_rejects_non_kde_env(monkeypatch):
    monkeypatch.setattr(
        plat_kio.os,
        "environ",
        {
            "XDG_CURRENT_DESKTOP": "GNOME",
            "XDG_SESSION_DESKTOP": "",
            "DESKTOP_SESSION": "",
        },
        raising=False,
    )
    assert plat_kio._is_kde_session() is False


def test_send2trash_builds_kio_move_command(monkeypatch):
    calls = {}

    def fake_which(name):
        return "/usr/bin/kioclient5" if name == "kioclient5" else None

    def fake_run(command, check, capture_output, text):
        calls["command"] = command
        calls["check"] = check
        calls["capture_output"] = capture_output
        calls["text"] = text
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(plat_kio.shutil, "which", fake_which)
    monkeypatch.setattr(plat_kio.subprocess, "run", fake_run)

    plat_kio.send2trash(["/tmp/send2trash test.txt"])

    assert calls["command"] == [
        "/usr/bin/kioclient5",
        "move",
        "file:///tmp/send2trash%20test.txt",
        "trash:/",
    ]
    assert calls["check"] is True
    assert calls["capture_output"] is True
    assert calls["text"] is True


def test_is_available_returns_false_outside_kde(monkeypatch):
    monkeypatch.setattr(plat_kio, "_is_kde_session", lambda: False)
    assert plat_kio.is_available() is False


def test_send2trash_raises_oserror_on_kio_failure(monkeypatch):
    def fake_which(name):
        return "/usr/bin/kioclient5" if name == "kioclient5" else None

    def fake_run(command, check, capture_output, text):
        raise subprocess.CalledProcessError(
            1,
            command,
            output="",
            stderr="Unable to create KIO worker",
        )

    monkeypatch.setattr(plat_kio.shutil, "which", fake_which)
    monkeypatch.setattr(plat_kio.subprocess, "run", fake_run)

    with pytest.raises(OSError, match="Unable to create KIO worker"):
        plat_kio.send2trash(["/tmp/send2trash test.txt"])


def test_is_available_returns_false_when_worker_probe_fails(monkeypatch):
    def fake_which(name):
        return "/usr/bin/kioclient5" if name == "kioclient5" else None

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 1, stdout="", stderr="")

    monkeypatch.setattr(plat_kio.shutil, "which", fake_which)
    monkeypatch.setattr(plat_kio.subprocess, "run", fake_run)

    assert plat_kio.is_available() is False
