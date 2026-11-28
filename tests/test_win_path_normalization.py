"""Tests for Windows path normalization in legacy and modern backends."""
import importlib
import sys
import types

import pytest

if sys.platform != "win32":
    pytest.skip("Windows path normalization tests", allow_module_level=True)

from send2trash.win import legacy  # noqa: E402


@pytest.mark.parametrize(
    "make_path",
    [
        lambda p: p.as_posix(),
        lambda p: f"{p.parent.parent}/sub\\{p.name}",
        lambda p: f"\\\\?\\{p.as_posix()}",
    ],
)
def test_legacy_normalizes_forward_and_mixed_slashes(tmp_path, monkeypatch, make_path):
    target = tmp_path / "sub" / "clip.mp4"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("data", encoding="utf-8")

    input_path = make_path(target)
    seen_pfrom = []

    def fake_sh_file_op(fileop_ptr):
        seen_pfrom.append(fileop_ptr._obj.pFrom)
        return 0

    monkeypatch.setattr(legacy, "SHFileOperationW", fake_sh_file_op)

    legacy.send2trash(input_path)

    assert len(seen_pfrom) == 1
    assert "/" not in seen_pfrom[0]


def test_modern_normalizes_forward_and_mixed_slashes(monkeypatch):
    seen_paths = []

    class DummyFileOp:
        def SetOperationFlags(self, flags):
            pass

        def DeleteItem(self, item, sink):
            pass

        def PerformOperations(self):
            return 0

        def GetAnyOperationsAborted(self):
            return False

    fake_pythoncom = types.ModuleType("pythoncom")
    fake_pythoncom.CLSCTX_ALL = 0
    fake_pythoncom.CoInitialize = lambda: None
    fake_pythoncom.CoUninitialize = lambda: None
    fake_pythoncom.CoCreateInstance = lambda *args: DummyFileOp()
    fake_pythoncom.WrapObject = lambda obj, iid: obj

    fake_pywintypes = types.ModuleType("pywintypes")
    fake_pywintypes.com_error = type("com_error", (Exception,), {})

    fake_shell = types.ModuleType("win32com.shell.shell")
    fake_shell.CLSID_FileOperation = "clsid"
    fake_shell.IID_IFileOperation = "iid_fileop"
    fake_shell.IID_IShellItem = "iid_shellitem"
    fake_shell.IID_IFileOperationProgressSink = "iid_sink"

    def fake_create_item(path, *_args):
        seen_paths.append(path)
        return object()

    fake_shell.SHCreateItemFromParsingName = fake_create_item

    fake_shellcon = types.ModuleType("win32com.shell.shellcon")
    fake_shellcon.FOF_NOCONFIRMATION = 1
    fake_shellcon.FOF_NOERRORUI = 2
    fake_shellcon.FOF_SILENT = 4
    fake_shellcon.FOFX_EARLYFAILURE = 8
    fake_shellcon.FOF_ALLOWUNDO = 16
    fake_shellcon.TSF_DELETE_RECYCLE_IF_POSSIBLE = 1
    fake_shellcon.SHGDN_FORPARSING = 0

    fake_policy = types.ModuleType("win32com.server.policy")
    fake_policy.DesignatedWrapPolicy = type("DesignatedWrapPolicy", (), {"_wrap_": lambda self, obj: None})

    fake_win32com = types.ModuleType("win32com")
    fake_win32com_shell = types.ModuleType("win32com.shell")
    fake_win32com_shell.shell = fake_shell
    fake_win32com_shell.shellcon = fake_shellcon
    fake_win32com_server = types.ModuleType("win32com.server")
    fake_win32com_server.policy = fake_policy

    for name, mod in [
        ("pythoncom", fake_pythoncom),
        ("pywintypes", fake_pywintypes),
        ("win32com", fake_win32com),
        ("win32com.shell", fake_win32com_shell),
        ("win32com.shell.shell", fake_shell),
        ("win32com.shell.shellcon", fake_shellcon),
        ("win32com.server", fake_win32com_server),
        ("win32com.server.policy", fake_policy),
    ]:
        monkeypatch.setitem(sys.modules, name, mod)

    monkeypatch.delitem(sys.modules, "send2trash.win.modern", raising=False)
    monkeypatch.delitem(sys.modules, "send2trash.win.IFileOperationProgressSink", raising=False)
    modern = importlib.import_module("send2trash.win.modern")
    try:
        modern.send2trash(["D:/temp/clip.mp4", "\\\\?\\D:/temp\\other.mp4"])
    finally:
        sys.modules.pop("send2trash.win.modern", None)
        sys.modules.pop("send2trash.win.IFileOperationProgressSink", None)

    assert seen_paths == ["D:\\temp\\clip.mp4", "D:\\temp\\other.mp4"]
