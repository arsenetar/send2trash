import runpy
import sys
import types
from pathlib import Path

import pytest


SELECTOR = Path(__file__).parents[1] / "send2trash" / "mac" / "__init__.py"
LEGACY = Path(__file__).parents[1] / "send2trash" / "mac" / "legacy.py"


def select_backend(monkeypatch, version, modern_available=True):
    modern = types.ModuleType("send2trash.mac.modern")
    legacy = types.ModuleType("send2trash.mac.legacy")
    modern.send2trash = object()
    legacy.send2trash = object()

    monkeypatch.setattr("platform.mac_ver", lambda: (version, ("", "", ""), ""))
    monkeypatch.setitem(sys.modules, modern.__name__, modern if modern_available else None)
    monkeypatch.setitem(sys.modules, legacy.__name__, legacy)

    namespace = runpy.run_path(str(SELECTOR))
    return namespace["send2trash"], {"modern": modern.send2trash, "legacy": legacy.send2trash}


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("14.0", "modern"),
        ("10.9", "modern"),
        ("10.8", "legacy"),
        ("", "modern"),
    ],
)
def test_select_backend(monkeypatch, version, expected):
    selected, backends = select_backend(monkeypatch, version)

    assert selected is backends[expected]


@pytest.mark.parametrize("version", ["14.0", ""])
def test_modern_version_falls_back_when_modern_backend_is_unavailable(monkeypatch, version):
    selected, backends = select_backend(monkeypatch, version, modern_available=False)

    assert selected is backends["legacy"]


class _DummyLib:
    def __init__(self, symbols):
        for name, value in symbols.items():
            setattr(self, name, value)


@pytest.mark.parametrize(
    ("foundation_has_symbol", "core_services_has_symbol", "expected_msg"),
    [
        (True, False, "from Foundation"),
        (False, True, "from CoreServices"),
        (False, False, "OSStatus error -43"),
    ],
)
def test_legacy_missing_status_comment_symbol(
    monkeypatch, foundation_has_symbol, core_services_has_symbol, expected_msg
):
    foundation_symbols = {}
    if foundation_has_symbol:
        foundation_symbols["GetMacOSStatusCommentString"] = lambda _code: b"from Foundation"

    core_symbols = {
        "FSPathMakeRefWithOptions": lambda *args: 0,
        "FSMoveObjectToTrashSync": lambda *args: 0,
    }
    if core_services_has_symbol:
        core_symbols["GetMacOSStatusCommentString"] = lambda _code: b"from CoreServices"

    libs = {
        "Foundation": _DummyLib(foundation_symbols),
        "CoreServices": _DummyLib(core_symbols),
    }
    monkeypatch.setattr("ctypes.util.find_library", lambda name: name)
    monkeypatch.setattr("ctypes.cdll.LoadLibrary", lambda name: libs[name])

    namespace = runpy.run_path(str(LEGACY))
    with pytest.raises(OSError, match=expected_msg):
        namespace["check_op_result"](-43)
