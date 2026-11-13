import ctypes
import os
import shutil
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


@pytest.fixture(name="unc_file")
def fixture_unc_file(test_file):
    # The test file reached through the administrative share, which Windows treats as a network location
    drive, rest = op.splitdrive(test_file[4:])
    unc_file = "\\\\localhost\\" + drive[0] + "$" + rest
    if not op.exists(unc_file):
        pytest.skip("Administrative share is not accessible")
    yield unc_file


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


def _long_paths_enabled():
    # Only long path aware processes have Windows refuse to recycle paths of MAX_PATH (260) characters or
    # more: LongPathsEnabled must be set and the executable must opt in, as python.exe does
    try:
        return bool(ctypes.WINFUNCTYPE(ctypes.c_ubyte)(("RtlAreLongPathsEnabled", ctypes.windll.ntdll))())
    except AttributeError:  # not exported before Windows 10 1607
        return False


def _trash_not_recyclable(file, fcn):
    # Windows would delete the file permanently instead of recycling it, so it must be left alone
    pytest.raises(TrashPermissionError, fcn, file)
    assert op.exists(file) is True


def _trash_not_recyclable_multifile(files, fcn):
    pytest.raises(TrashPermissionError, fcn, files)
    assert all(op.exists(file) for file in files) is True


def _trash_locked_file(files, fcn):
    # The first file is held open without delete sharing, so trashing fails on it: the error must say so and
    # name it rather than the last file
    with open(files[0], "a", encoding="utf-8"):
        with pytest.raises(PermissionError) as error:
            fcn(files)
    assert not isinstance(error.value, TrashPermissionError)
    assert op.basename(error.value.filename) == op.basename(files[0])
    assert all(op.exists(file) for file in files) is True


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


# NOTE: in long path aware processes Windows deletes paths of MAX_PATH (260) characters or more
# permanently instead of recycling them, which the modern version refuses to do. Otherwise they are recycled.
def test_trash_long_file_modern(long_file):
    if _long_paths_enabled():
        _trash_not_recyclable(long_file, s2t_modern)
    else:
        _trash_file(long_file, s2t_modern)


def test_trash_long_multifile_modern(long_files):
    if _long_paths_enabled():
        _trash_not_recyclable_multifile(long_files, s2t_modern)
    else:
        _trash_multifile(long_files, s2t_modern)


def test_trash_unc_file_modern(unc_file):
    _trash_not_recyclable(unc_file, s2t_modern)


def test_trash_mixed_multifile_modern(test_files, unc_file):
    # Windows decides whether to recycle for all the files at once, a single network file would otherwise get
    # the local files deleted permanently too
    _trash_not_recyclable_multifile(test_files + [unc_file], s2t_modern)


def test_trash_locked_file_modern(test_files):
    _trash_locked_file(test_files, s2t_modern)


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


def test_trash_long_file_legacy(long_file):
    _trash_file(long_file, s2t_legacy)


def test_trash_long_multifile_legacy(long_files):
    _trash_multifile(long_files, s2t_legacy)


def test_trash_nothing_legacy():
    try:
        s2t_legacy([])
    except Exception as ex:
        assert False, f"Exception thrown when trashing nothing: {ex}"
