import os
import shutil
import subprocess
import sys
from os import path as op
import pytest
from send2trash import send2trash as s2t
from send2trash.exceptions import TrashPermissionError

s2t_modern = None
s2t_legacy = None

if sys.platform != "win32":
    pytest.skip("Skipping windows-only tests", allow_module_level=True)
else:
    # import the two versions as well as the "automatic" version
    from send2trash.win.modern import send2trash as s2t_modern
    from send2trash.win.legacy import send2trash as s2t_legacy
    from send2trash.win.legacy import long_paths_enabled, too_long_to_recycle, utf16_len

if s2t_modern is None:
    pytest.fail("Modern send2trash not available")

if s2t_legacy is None:
    pytest.fail("Legacy send2trash not available")


def _create_tree(path):
    dir_name = op.dirname(path)
    if not op.isdir(dir_name):
        os.makedirs(dir_name)
    with open(path, "w", encoding="utf-8") as writer:
        writer.write("send2trash test")


@pytest.fixture(name="test_dir")
def fixture_test_dir(tmp_path):
    dir_name = "\\\\?\\" + str(tmp_path)
    assert op.exists(dir_name) is True
    yield dir_name
    shutil.rmtree(dir_name, ignore_errors=True)


@pytest.fixture(name="test_file")
def fixture_test_file(test_dir):
    file = op.join(test_dir, "testfile.txt")
    _create_tree(file)
    assert op.exists(file) is True
    yield file
    # Note dir will cleanup the file


@pytest.fixture(name="test_files")
def fixture_test_files(test_dir):
    files = [op.join(test_dir, f"testfile{index}.txt") for index in range(10)]
    for file in files:
        _create_tree(file)
    assert all(op.exists(file) for file in files) is True
    yield files
    # Note dir will cleanup the files


# Long path tests
@pytest.fixture(name="long_dir")
def fixture_long_dir(tmp_path):
    dir_name = "\\\\?\\" + str(tmp_path)
    name = "A" * 100
    yield op.join(dir_name, name, name, name)
    try:
        shutil.rmtree(dir_name, ignore_errors=True)
    except TypeError:
        pass


@pytest.fixture(name="long_file")
def fixture_long_file(long_dir):
    name = "A" * 100
    path = op.join(long_dir, name + "{}.txt")
    file = path.format("")
    _create_tree(file)
    assert op.exists(file) is True
    yield file


@pytest.fixture(name="long_files")
def fixture_long_files(long_dir):
    name = "A" * 100
    path = op.join(long_dir, name + "{}.txt")
    files = [path.format(index) for index in range(10)]
    for file in files:
        _create_tree(file)
    assert all(op.exists(file) for file in files) is True
    yield files


def _trash_folder(folder, fcn):
    fcn(folder)
    assert op.exists(folder) is False


def _trash_file(file, fcn):
    fcn(file)
    assert op.exists(file) is False


def _trash_multifile(files, fcn):
    fcn(files)
    assert any(op.exists(file) for file in files) is False


def _file_not_found(folder, fcn):
    file = op.join(folder, "otherfile.txt")
    pytest.raises(OSError, fcn, file)


def _multi_byte_unicode(folder, fcn):
    single_file = op.join(folder, "😇.txt")
    _create_tree(single_file)
    assert op.exists(single_file) is True
    fcn(single_file)
    assert op.exists(single_file) is False
    files = [op.join(folder, f"😇{index}.txt") for index in range(10)]
    for file in files:
        _create_tree(file)
    assert all(op.exists(file) for file in files) is True
    fcn(files)
    assert any(op.exists(file) for file in files) is False


def test_trash_folder(test_dir):
    _trash_folder(test_dir, s2t)


def test_trash_file(test_file):
    _trash_file(test_file, s2t)


def test_trash_multifile(test_files):
    _trash_multifile(test_files, s2t)


def test_file_not_found(test_dir):
    _file_not_found(test_dir, s2t)


def test_trash_folder_modern(test_dir):
    _trash_folder(test_dir, s2t_modern)


def test_trash_file_modern(test_file):
    _trash_file(test_file, s2t_modern)


def test_trash_multifile_modern(test_files):
    _trash_multifile(test_files, s2t_modern)


def test_file_not_found_modern(test_dir):
    _file_not_found(test_dir, s2t_modern)


def test_multi_byte_unicode_modern(test_dir):
    _multi_byte_unicode(test_dir, s2t_modern)


# NOTE: both legacy and modern test "pass" on windows, however sometimes with the same path
# they do not actually recycle files but delete them.  Noticed this when testing with the
# recycle bin open, noticed later tests actually worked, modern version can actually detect
# when this happens but not stop it at this moment, and we need a way to verify it when testing.
def test_trash_long_file_modern(long_file):
    _trash_file(long_file, s2t_modern)


def test_trash_long_multifile_modern(long_files):
    _trash_multifile(long_files, s2t_modern)


def test_trash_nothing_modern():
    try:
        s2t_modern([])
    except Exception as ex:
        assert False, f"Exception thrown when trashing nothing: {ex}"


def test_trash_folder_legacy(test_dir):
    _trash_folder(test_dir, s2t_legacy)


def test_trash_file_legacy(test_file):
    _trash_file(test_file, s2t_legacy)


def test_trash_multifile_legacy(test_files):
    _trash_multifile(test_files, s2t_legacy)


def test_file_not_found_legacy(test_dir):
    _file_not_found(test_dir, s2t_legacy)


def test_multi_byte_unicode_legacy(test_dir):
    _multi_byte_unicode(test_dir, s2t_legacy)


@pytest.fixture(name="long_paths_on")
def fixture_long_paths_on(monkeypatch):
    monkeypatch.setattr("send2trash.win.legacy.long_paths_enabled", lambda: True)


@pytest.fixture(name="long_paths_off")
def fixture_long_paths_off(monkeypatch):
    monkeypatch.setattr("send2trash.win.legacy.long_paths_enabled", lambda: False)


def test_long_paths_disabled_without_export_legacy(monkeypatch):
    monkeypatch.setattr("send2trash.win.legacy.RtlAreLongPathsEnabled", None)
    assert long_paths_enabled() is False


# A long-path aware process makes SHFileOperationW delete a path of MAX_PATH UTF-16 code units or more
# permanently instead of recycling it, so the legacy backend refuses it and leaves it in place.
@pytest.mark.usefixtures("long_paths_on")
def test_trash_long_file_legacy(long_file):
    pytest.raises(TrashPermissionError, s2t_legacy, long_file)
    assert op.exists(long_file) is True


@pytest.mark.usefixtures("long_paths_on")
def test_trash_long_multifile_legacy(long_files):
    pytest.raises(TrashPermissionError, s2t_legacy, long_files)
    assert all(op.exists(file) for file in long_files) is True


# Without long-path awareness SHFileOperationW recycles these paths, so nothing is refused. Only the missing
# refusal is checked: on a machine that is in fact long-path aware the call still deletes them permanently.
@pytest.mark.usefixtures("long_paths_off")
def test_trash_long_file_long_paths_off_legacy(long_file):
    _trash_file(long_file, s2t_legacy)


@pytest.mark.usefixtures("long_paths_off")
def test_trash_long_multifile_long_paths_off_legacy(long_files):
    _trash_multifile(long_files, s2t_legacy)


@pytest.mark.usefixtures("long_paths_on")
def test_trash_folder_holding_long_path_legacy(long_file, tmp_path):
    folder = op.join(str(tmp_path), "A" * 100)
    pytest.raises(TrashPermissionError, s2t_legacy, folder)
    assert op.exists(long_file) is True


def _emoji_child(tmp_path, units):
    # Each 😇 is one character to len() but two UTF-16 code units to MAX_PATH.
    folder = op.join(str(tmp_path), "emoji")
    stem = op.join(folder, "A" * 100, "")
    room = units - utf16_len(stem) - len(".txt")
    child = stem + "😇" * (room // 2) + "B" * (room % 2) + ".txt"
    _create_tree("\\\\?\\" + child)
    assert utf16_len(child) == units
    return folder, child


@pytest.mark.usefixtures("long_paths_on")
def test_trash_folder_holding_long_utf16_path_legacy(tmp_path):
    folder, child = _emoji_child(tmp_path, 260)
    assert len(child) < 260
    pytest.raises(TrashPermissionError, s2t_legacy, folder)
    assert op.exists("\\\\?\\" + child) is True


def test_utf16_path_below_max_path_not_refused_legacy(tmp_path):
    folder, _ = _emoji_child(tmp_path, 259)
    assert too_long_to_recycle(folder) is None


# The \\?\ prefix never reaches SHFileOperationW, so it must not count towards MAX_PATH.
def test_long_path_prefix_not_counted_legacy(tmp_path):
    file = op.join(str(tmp_path), "A" * (258 - utf16_len(str(tmp_path)) - 1))
    _create_tree("\\\\?\\" + file)
    assert too_long_to_recycle("\\\\?\\" + file) is None


# The shell recycles a junction as a link, so a path that only reaches MAX_PATH through one is not refused.
def test_junction_not_followed_legacy(tmp_path):
    target = op.join(str(tmp_path), "target")
    folder = op.join(str(tmp_path), "folder")
    junction = op.join(folder, "J" * 40)
    stem = op.join(target, "A" * 50, "")
    leaf = stem + "B" * (250 - utf16_len(stem) - len(".txt")) + ".txt"
    _create_tree(leaf)
    os.makedirs(folder)
    subprocess.run(["cmd", "/c", "mklink", "/J", junction, target], check=True, capture_output=True)
    assert utf16_len(leaf.replace(target, junction)) >= 260
    assert too_long_to_recycle(folder) is None
    assert too_long_to_recycle(junction) is None


def test_trash_nothing_legacy():
    try:
        s2t_legacy([])
    except Exception as ex:
        assert False, f"Exception thrown when trashing nothing: {ex}"
