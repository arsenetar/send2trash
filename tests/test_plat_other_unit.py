"""Cross-platform unit tests for Freedesktop plat_other mount-point resolution."""
import importlib
import os
import posixpath
import sys
import types


def _load_plat_other(monkeypatch):
    if not hasattr(os, "environb"):
        monkeypatch.setattr(os, "environb", {b"XDG_DATA_HOME": b"/home/user/.local/share"}, raising=False)
    if not hasattr(os, "getuid"):
        monkeypatch.setattr(os, "getuid", lambda: 1000, raising=False)
    monkeypatch.delitem(sys.modules, "send2trash.plat_other", raising=False)
    plat_other = importlib.import_module("send2trash.plat_other")
    fake_op = types.ModuleType("posixpath")
    fake_op.__dict__.update(posixpath.__dict__)
    monkeypatch.setattr(plat_other, "op", fake_op)
    return plat_other, fake_op


def test_find_mount_point_skips_non_directory_file(monkeypatch):
    plat_other, fake_op = _load_plat_other(monkeypatch)
    try:
        file_path = b"/nanshe_workflow/data.tif"
        mount_dir = b"/nanshe_workflow"

        monkeypatch.setattr(fake_op, "realpath", lambda p: p)
        monkeypatch.setattr(fake_op, "isdir", lambda p: p in (mount_dir, b"/"))
        monkeypatch.setattr(fake_op, "ismount", lambda p: p in (file_path, mount_dir, b"/"))

        assert plat_other.find_mount_point(file_path) == mount_dir
    finally:
        sys.modules.pop("send2trash.plat_other", None)


def test_send2trash_does_not_create_trash_inside_file(monkeypatch):
    plat_other, fake_op = _load_plat_other(monkeypatch)
    try:
        file_path = b"/nanshe_workflow/data.tif"
        mount_dir = b"/nanshe_workflow"
        home_dir = b"/home/user"
        created_dirs = []
        moved = []

        monkeypatch.setattr(fake_op, "realpath", lambda p: p)
        monkeypatch.setattr(fake_op, "expanduser", lambda p: home_dir if p == b"~" else p)
        monkeypatch.setattr(fake_op, "exists", lambda p: p == file_path)
        monkeypatch.setattr(fake_op, "isdir", lambda p: p in (mount_dir, b"/"))
        monkeypatch.setattr(fake_op, "ismount", lambda p: p in (file_path, mount_dir, b"/"))
        monkeypatch.setattr(os, "access", lambda p, mode: True)
        monkeypatch.setattr(plat_other, "get_dev", lambda p: 1 if p == home_dir else 2)

        def fake_makedirs(folder, mode=0o700):
            if folder.startswith(file_path + b"/"):
                raise NotADirectoryError(20, "Not a directory", folder)
            created_dirs.append(folder)

        monkeypatch.setattr(os, "makedirs", fake_makedirs)
        monkeypatch.setattr(
            plat_other,
            "trash_move",
            lambda src, dst, topdir=None, cross_dev=False: moved.append((src, dst, topdir)),
        )

        plat_other.send2trash(file_path)

        assert created_dirs == [b"/nanshe_workflow/.Trash-1000"]
        assert moved == [(file_path, b"/nanshe_workflow/.Trash-1000", mount_dir)]
    finally:
        sys.modules.pop("send2trash.plat_other", None)
