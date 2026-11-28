"""Cross-platform unit tests for Freedesktop plat_other overlayfs device handling."""
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


def test_overlayfs_file_in_home_uses_hometrash(monkeypatch):
    plat_other, fake_op = _load_plat_other(monkeypatch)
    try:
        home_dir = b"/home/user"
        sub_dir = b"/home/user/overlay"
        file_path = b"/home/user/overlay/upper.txt"
        moved = []

        dirs = {b"/", home_dir, sub_dir}
        devs = {
            b"/": 1,
            home_dir: 10,
            sub_dir: 10,
            file_path: 20,  # Upper-layer file reports different st_dev in overlayfs.
        }

        monkeypatch.setattr(fake_op, "abspath", lambda p: p)
        monkeypatch.setattr(fake_op, "realpath", lambda p: p)
        monkeypatch.setattr(fake_op, "expanduser", lambda p: home_dir if p == b"~" else p)
        monkeypatch.setattr(fake_op, "exists", lambda p: p == file_path)
        monkeypatch.setattr(fake_op, "isdir", lambda p: p in dirs)
        monkeypatch.setattr(fake_op, "islink", lambda _p: False)
        monkeypatch.setattr(fake_op, "ismount", lambda p: p in (b"/", home_dir))
        monkeypatch.setattr(os, "access", lambda p, mode: True)
        monkeypatch.setattr(plat_other, "get_dev", lambda p: devs[p])
        monkeypatch.setattr(
            plat_other,
            "trash_move",
            lambda src, dst, topdir=None, cross_dev=False: moved.append((src, dst, topdir)),
        )

        plat_other.send2trash(file_path)

        assert moved == [(file_path, plat_other.HOMETRASH_B, plat_other.XDG_DATA_HOME)]
    finally:
        sys.modules.pop("send2trash.plat_other", None)


def test_overlayfs_file_on_external_mount_uses_external_trash(monkeypatch):
    plat_other, fake_op = _load_plat_other(monkeypatch)
    try:
        home_dir = b"/home/user"
        mount_dir = b"/mnt/overlay"
        sub_dir = b"/mnt/overlay/sub"
        file_path = b"/mnt/overlay/sub/upper.txt"
        moved = []

        dirs = {b"/", home_dir, mount_dir, sub_dir}
        devs = {
            b"/": 1,
            home_dir: 10,
            mount_dir: 30,
            sub_dir: 30,
            file_path: 40,  # Upper-layer file reports different st_dev in overlayfs.
        }

        monkeypatch.setattr(fake_op, "abspath", lambda p: p)
        monkeypatch.setattr(fake_op, "realpath", lambda p: p)
        monkeypatch.setattr(fake_op, "expanduser", lambda p: home_dir if p == b"~" else p)
        monkeypatch.setattr(fake_op, "exists", lambda p: p == file_path)
        monkeypatch.setattr(fake_op, "isdir", lambda p: p in dirs)
        monkeypatch.setattr(fake_op, "islink", lambda _p: False)
        monkeypatch.setattr(fake_op, "ismount", lambda p: p in (b"/", mount_dir))
        monkeypatch.setattr(os, "access", lambda p, mode: True)
        monkeypatch.setattr(plat_other, "get_dev", lambda p: devs[p])
        monkeypatch.setattr(plat_other, "find_ext_volume_trash", lambda root: fake_op.join(root, b".Trash-1000"))
        monkeypatch.setattr(
            plat_other,
            "trash_move",
            lambda src, dst, topdir=None, cross_dev=False: moved.append((src, dst, topdir)),
        )

        plat_other.send2trash(file_path)

        assert moved == [(file_path, b"/mnt/overlay/.Trash-1000", mount_dir)]
    finally:
        sys.modules.pop("send2trash.plat_other", None)


def test_overlayfs_symlink_and_directory_device_selection(monkeypatch):
    plat_other, fake_op = _load_plat_other(monkeypatch)
    try:
        home_dir = b"/home/user"
        ext_mount = b"/mnt/ext"
        ext_sub = b"/mnt/ext/sub"
        symlink_in_home = b"/home/user/link_to_ext"
        moved = []

        dirs = {b"/", home_dir, ext_mount, ext_sub, symlink_in_home}
        devs = {
            b"/": 1,
            home_dir: 10,
            ext_mount: 30,
            ext_sub: 30,
        }

        monkeypatch.setattr(fake_op, "abspath", lambda p: p)
        monkeypatch.setattr(fake_op, "realpath", lambda p: ext_sub if p == symlink_in_home else p)
        monkeypatch.setattr(fake_op, "expanduser", lambda p: home_dir if p == b"~" else p)
        monkeypatch.setattr(fake_op, "exists", lambda p: p in (symlink_in_home, ext_sub))
        monkeypatch.setattr(fake_op, "isdir", lambda p: p in dirs)
        monkeypatch.setattr(fake_op, "islink", lambda p: p == symlink_in_home)
        monkeypatch.setattr(fake_op, "ismount", lambda p: p in (b"/", ext_mount))
        monkeypatch.setattr(os, "access", lambda p, mode: True)
        monkeypatch.setattr(plat_other, "get_dev", lambda p: devs[p])
        monkeypatch.setattr(plat_other, "find_ext_volume_trash", lambda root: fake_op.join(root, b".Trash-1000"))
        monkeypatch.setattr(
            plat_other,
            "trash_move",
            lambda src, dst, topdir=None, cross_dev=False: moved.append((src, dst, topdir)),
        )

        plat_other.send2trash(symlink_in_home)
        plat_other.send2trash(ext_sub)

        assert moved == [
            (symlink_in_home, plat_other.HOMETRASH_B, plat_other.XDG_DATA_HOME),
            (ext_sub, b"/mnt/ext/.Trash-1000", ext_mount),
        ]
    finally:
        sys.modules.pop("send2trash.plat_other", None)
