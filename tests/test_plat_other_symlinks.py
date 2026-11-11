import errno
import os
from configparser import ConfigParser
from os import path as op
import sys
from urllib.parse import unquote

import pytest

if sys.platform == "win32":
    pytest.skip("The Freedesktop backend requires POSIX", allow_module_level=True)
else:
    from send2trash import plat_other


@pytest.fixture(name="trash")
def fixture_trash(tmp_path, monkeypatch):
    data_home = tmp_path / "data"
    data_home.mkdir()
    trash = data_home / "Trash"
    monkeypatch.setattr(plat_other, "XDG_DATA_HOME", os.fsencode(data_home))
    monkeypatch.setattr(plat_other, "HOMETRASH_B", os.fsencode(trash))
    monkeypatch.setattr(plat_other, "HOMETRASH", str(trash))

    # Keep all tests on tmp_path's device even if the user's home is elsewhere.
    original_get_dev = plat_other.get_dev
    home = op.expanduser(b"~")

    def get_dev(path):
        if path == home:
            return os.lstat(tmp_path).st_dev
        return original_get_dev(path)

    monkeypatch.setattr(plat_other, "get_dev", get_dev)
    return trash


def read_original_path(info_file):
    info = ConfigParser()
    info.read(info_file, encoding="utf-8")
    return unquote(info.get("Trash Info", "Path", raw=True))


@pytest.mark.parametrize("path_type", [str, os.fsencode, lambda path: path])
@pytest.mark.parametrize("absolute_target", [False, True])
def test_trash_broken_symlink(tmp_path, trash, path_type, absolute_target):
    source = tmp_path / "link"
    target = str(tmp_path / "missing") if absolute_target else "missing"
    source.symlink_to(target)

    plat_other.send2trash(path_type(source))

    assert not op.lexists(source)
    assert (trash / "files" / "link").is_symlink()
    assert os.readlink(trash / "files" / "link") == target
    assert not (tmp_path / "missing").exists()
    assert read_original_path(trash / "info" / "link.trashinfo") == str(source)


def test_trash_relative_broken_symlink(tmp_path, trash, monkeypatch):
    source = tmp_path / "link"
    source.symlink_to("missing")
    monkeypatch.chdir(tmp_path)

    plat_other.send2trash("link")

    assert not op.lexists(source)
    assert os.readlink(trash / "files" / "link") == "missing"
    assert read_original_path(trash / "info" / "link.trashinfo") == str(source)


def test_trash_symlink_to_read_only_target(tmp_path, trash):
    target = tmp_path / "target"
    target.write_text("keep this target", encoding="utf-8")
    target.chmod(0o400)
    source = tmp_path / "link"
    source.symlink_to(target)

    plat_other.send2trash(source)

    assert not op.lexists(source)
    assert os.readlink(trash / "files" / "link") == str(target)
    assert target.read_text(encoding="utf-8") == "keep this target"
    assert target.stat().st_mode & 0o777 == 0o400


def test_symlink_requires_writable_parent(tmp_path, trash):
    parent = tmp_path / "read-only"
    parent.mkdir()
    target = tmp_path / "target"
    target.touch()
    source = parent / "link"
    source.symlink_to(target)
    parent.chmod(0o500)
    try:
        if os.access(parent, os.W_OK | os.X_OK):
            pytest.skip("Current user can write to read-only directories")

        with pytest.raises(OSError) as exc:
            plat_other.send2trash(source)

        assert exc.value.errno == errno.EACCES
        assert source.is_symlink()
        assert not trash.exists()
    finally:
        parent.chmod(0o700)


def test_read_only_regular_file_keeps_permission_check(tmp_path, trash):
    source = tmp_path / "read-only"
    source.touch()
    source.chmod(0o400)
    if os.access(source, os.W_OK):
        pytest.skip("Current user can write to read-only files")

    with pytest.raises(OSError) as exc:
        plat_other.send2trash(source)

    assert exc.value.errno == errno.EACCES
    assert source.exists()
    assert not trash.exists()


@pytest.mark.parametrize("collision_dir", ["files", "info"])
def test_broken_trash_symlink_reserves_its_name(tmp_path, trash, collision_dir):
    (trash / "files").mkdir(parents=True)
    (trash / "info").mkdir()
    collision_name = "item" if collision_dir == "files" else "item.trashinfo"
    collision = trash / collision_dir / collision_name
    collision.symlink_to("old-missing-target")
    source = tmp_path / "item"
    source.write_text("new contents", encoding="utf-8")

    plat_other.send2trash(source)

    assert collision.is_symlink()
    assert os.readlink(collision) == "old-missing-target"
    assert not (collision.parent / "old-missing-target").exists()
    assert (trash / "files" / "item 1").read_text(encoding="utf-8") == "new contents"
    assert read_original_path(trash / "info" / "item 1.trashinfo") == str(source)


@pytest.mark.parametrize("target_exists", [False, True])
@pytest.mark.parametrize("parent_alias", [False, True])
def test_symlink_uses_its_own_volume(tmp_path, trash, monkeypatch, target_exists, parent_alias):
    volume = tmp_path / "volume"
    volume.mkdir()
    target = tmp_path / "target"
    if target_exists:
        target.write_text("keep this target", encoding="utf-8")
    source = volume / "link"
    source.symlink_to(target)
    if parent_alias:
        alias = tmp_path / "volume-alias"
        alias.symlink_to(volume, target_is_directory=True)
        source = alias / "link"

    volume_b = os.fsencode(volume)
    original_get_dev = plat_other.get_dev
    original_ismount = op.ismount

    def get_dev(path):
        path = os.fsencode(path)
        # Model lstat: the final link belongs to its parent's device, not its target's.
        if path == volume_b or op.realpath(op.dirname(path)) == volume_b:
            return "external device"
        return original_get_dev(path)

    def ismount(path):
        return op.realpath(path) == volume_b or original_ismount(path)

    monkeypatch.setattr(plat_other, "get_dev", get_dev)
    monkeypatch.setattr(plat_other.op, "ismount", ismount)

    plat_other.send2trash(source)

    volume_trash = volume / (".Trash-" + str(os.getuid()))
    assert not op.lexists(source)
    assert os.readlink(volume_trash / "files" / "link") == str(target)
    assert read_original_path(volume_trash / "info" / "link.trashinfo") == "link"
    assert not trash.exists()
    assert target.exists() == target_exists
    if target_exists:
        assert target.read_text(encoding="utf-8") == "keep this target"


@pytest.mark.parametrize("path_type", [str, os.fsencode])
@pytest.mark.parametrize("inside", [False, True])
def test_info_uses_link_location_not_target(tmp_path, path_type, inside):
    topdir = tmp_path / "data"
    topdir.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    source = (topdir if inside else outside) / "link"
    target = (outside if inside else topdir) / "missing"
    source.symlink_to(target)

    info = ConfigParser()
    info.read_string(plat_other.info_for(path_type(source), path_type(topdir)))
    original = unquote(info.get("Trash Info", "Path", raw=True))

    assert original == ("link" if inside else str(source))
    assert ".." not in original.split(os.sep)


def test_info_resolves_parent_and_topdir_aliases(tmp_path):
    topdir = tmp_path / "data"
    topdir.mkdir()
    alias = tmp_path / "data-alias"
    alias.symlink_to(topdir, target_is_directory=True)
    source = alias / "link"
    source.symlink_to(tmp_path / "missing")

    info = ConfigParser()
    info.read_string(plat_other.info_for(os.fsencode(source), os.fsencode(alias)))

    assert info.get("Trash Info", "Path", raw=True) == "link"


@pytest.mark.parametrize("with_topdir", [False, True])
def test_info_preserves_absolute_outside_alias(tmp_path, with_topdir):
    topdir = tmp_path / "data"
    topdir.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    alias = tmp_path / "outside-alias"
    alias.symlink_to(outside, target_is_directory=True)
    source = alias / "link"
    source.symlink_to(tmp_path / "missing")

    info = ConfigParser()
    info.read_string(plat_other.info_for(os.fsencode(source), os.fsencode(topdir) if with_topdir else None))

    assert unquote(info.get("Trash Info", "Path", raw=True)) == str(source)


def test_missing_path_still_fails(tmp_path, trash):
    with pytest.raises(OSError) as exc:
        plat_other.send2trash(tmp_path / "missing")

    assert exc.value.errno == errno.ENOENT
    assert not trash.exists()
