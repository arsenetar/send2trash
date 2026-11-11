"""Mock-only tests for diagnostics from the Windows legacy backend."""
import sys

import pytest

if sys.platform != "win32":
    pytest.skip("Windows legacy backend diagnostics", allow_module_level=True)

from send2trash.win import legacy  # noqa: E402


def test_legacy_error_keeps_shell_code_and_original_caller_path(monkeypatch):
    caller_path = "synthetic-input\\loaded.dll"
    short_path = r"C:\SYNTHET~1\LOAD~1.DLL"
    monkeypatch.setattr(legacy, "get_short_path_name", lambda path: short_path)
    monkeypatch.setattr(legacy, "SHFileOperationW", lambda _fileop: 0x7C)
    monkeypatch.setattr(legacy, "FormatError", lambda error: "mapped error %s" % error)

    with pytest.raises(OSError) as raised:
        legacy.send2trash(caller_path)

    assert raised.value.filename == [caller_path]
    assert raised.value.winerror == 0xA1
    assert raised.value.sh_file_operation_result == 0x7C
