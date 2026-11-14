import os
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

import send2trash.plat_kio as plat_kio

if sys.platform in ("win32", "darwin"):
    pytest.skip("KIO is used on Freedesktop platforms only", allow_module_level=True)


@pytest.fixture(autouse=True)
def isolate_kio_state(monkeypatch):
    clear_cache = plat_kio._kioclient.cache_clear
    clear_cache()
    for name in ("KDE_FULL_SESSION", "XDG_CURRENT_DESKTOP", "XDG_SESSION_DESKTOP", "DESKTOP_SESSION"):
        monkeypatch.delenv(name, raising=False)
    yield
    clear_cache()


def test_kioclient_prefers_newest_available(monkeypatch):
    calls = []

    def fake_which(name):
        calls.append(name)
        return {
            "kioclient6": None,
            "kioclient5": "/usr/bin/kioclient5",
            "kioclient": "/usr/bin/kioclient",
        }[name]

    monkeypatch.setattr(plat_kio.shutil, "which", fake_which)
    assert plat_kio._kioclient() == "/usr/bin/kioclient5"
    assert plat_kio._kioclient() == "/usr/bin/kioclient5"
    assert calls == ["kioclient6", "kioclient5"]


def test_kioclient_missing_raises_oserror(monkeypatch):
    monkeypatch.setattr(plat_kio.shutil, "which", lambda name: None)
    with pytest.raises(FileNotFoundError, match="No kioclient executable found"):
        plat_kio._kioclient()


def test_is_kde_session_detects_kde_env(monkeypatch):
    monkeypatch.setenv("KDE_FULL_SESSION", "true")
    assert plat_kio._is_kde_session() is True


def test_is_kde_session_rejects_non_kde_env(monkeypatch):
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "GNOME")
    assert plat_kio._is_kde_session() is False


@pytest.mark.parametrize("name", ["XDG_CURRENT_DESKTOP", "XDG_SESSION_DESKTOP", "DESKTOP_SESSION"])
def test_is_kde_session_detects_desktop_values(monkeypatch, name):
    monkeypatch.setenv(name, "KDE:Plasma")
    assert plat_kio._is_kde_session() is True


@pytest.mark.parametrize("path", [b"/tmp/test-\xe9", os.fsdecode(b"/tmp/test-\xe9")])
def test_path_to_url_preserves_non_utf8_bytes(path):
    assert plat_kio._path_to_url(path) == "file:///tmp/test-%E9"


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


@pytest.mark.parametrize("returncode", [0, 1])
def test_is_available_checks_worker_probe(monkeypatch, returncode):
    monkeypatch.setenv("KDE_FULL_SESSION", "true")

    def fake_which(name):
        return "/usr/bin/kioclient5" if name == "kioclient5" else None

    def fake_run(*args, **kwargs):
        assert args[0] == ["/usr/bin/kioclient5", "stat", "trash:/"]
        assert kwargs == {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "timeout": 2,
            "check": False,
        }
        return subprocess.CompletedProcess(args[0], returncode, stdout="", stderr="")

    monkeypatch.setattr(plat_kio.shutil, "which", fake_which)
    monkeypatch.setattr(plat_kio.subprocess, "run", fake_run)

    assert plat_kio.is_available() is (returncode == 0)


def test_is_available_returns_false_when_client_missing(monkeypatch):
    monkeypatch.setenv("KDE_FULL_SESSION", "true")
    monkeypatch.setattr(plat_kio.shutil, "which", lambda name: None)
    assert plat_kio.is_available() is False


@pytest.mark.parametrize("error", [FileNotFoundError(), subprocess.TimeoutExpired("kioclient", 2)])
def test_is_available_handles_probe_errors(monkeypatch, error):
    monkeypatch.setenv("KDE_FULL_SESSION", "true")
    monkeypatch.setattr(plat_kio, "_kioclient", lambda: "/usr/bin/kioclient5")

    def fail_probe(*args, **kwargs):
        raise error

    monkeypatch.setattr(plat_kio.subprocess, "run", fail_probe)
    assert plat_kio.is_available() is False


def test_send2trash_handles_disappeared_client(monkeypatch):
    monkeypatch.setattr(plat_kio.shutil, "which", lambda name: "/usr/bin/kioclient5")
    assert plat_kio._kioclient() == "/usr/bin/kioclient5"

    def fail_run(*args, **kwargs):
        raise FileNotFoundError("kioclient disappeared")

    monkeypatch.setattr(plat_kio.subprocess, "run", fail_run)
    with pytest.raises(FileNotFoundError, match="kioclient disappeared"):
        plat_kio.send2trash("/tmp/test")


def test_backend_selection_is_lazy_and_cached(monkeypatch):
    probes = []
    trashed = []

    def available():
        probes.append(True)
        return True

    monkeypatch.setattr(plat_kio, "is_available", available)
    monkeypatch.setattr(plat_kio, "send2trash", trashed.append)
    namespace = runpy.run_path(str(Path(plat_kio.__file__).with_name("__init__.py")))
    assert probes == []

    namespace["send2trash"]("/tmp/first")
    namespace["send2trash"]("/tmp/second")
    assert probes == [True]
    assert trashed == ["/tmp/first", "/tmp/second"]


@pytest.mark.parametrize("gio_available", [True, False])
def test_backend_selection_falls_back_when_kio_unavailable(monkeypatch, gio_available):
    from types import ModuleType

    fallback = ModuleType("send2trash.plat_gio" if gio_available else "send2trash.plat_other")
    trashed = []
    fallback.send2trash = trashed.append
    monkeypatch.setattr(plat_kio, "is_available", lambda: False)
    monkeypatch.setitem(sys.modules, "send2trash.plat_gio", fallback if gio_available else None)
    if not gio_available:
        monkeypatch.setitem(sys.modules, "send2trash.plat_other", fallback)

    namespace = runpy.run_path(str(Path(plat_kio.__file__).with_name("__init__.py")))
    namespace["send2trash"]("/tmp/test")
    assert trashed == ["/tmp/test"]
