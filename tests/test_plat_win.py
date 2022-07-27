# encoding: utf-8
import os
import shutil
import sys
import pytest
from os import path as op

from send2trash import send2trash as s2t

# import the two versions as well as the "automatic" version
if sys.platform == "win32":
    from send2trash.win.modern import send2trash as s2t_modern
    from send2trash.win.legacy import send2trash as s2t_legacy
else:
    pytest.skip("Skipping windows-only tests", allow_module_level=True)


def _create_tree(path):
    dirname = op.dirname(path)
    if not op.isdir(dirname):
        os.makedirs(dirname)
    with open(path, "w") as writer:
        writer.write("send2trash test")


@pytest.fixture
def testdir(tmp_path):
    dirname = "\\\\?\\" + str(tmp_path)
    assert op.exists(dirname) is True
    yield dirname
    shutil.rmtree(dirname, ignore_errors=True)


@pytest.fixture
def testfile(testdir):
    file = op.join(testdir, "testfile.txt")
    _create_tree(file)
    assert op.exists(file) is True
    yield file
    # Note dir will cleanup the file


@pytest.fixture
def testfiles(testdir):
    files = [op.join(testdir, "testfile{}.txt".format(index)) for index in range(10)]
    [_create_tree(file) for file in files]
    assert all([op.exists(file) for file in files]) is True
    yield files
    # Note dir will cleanup the files


def _trash_folder(dir, fcn):
    fcn(dir)
    assert op.exists(dir) is False


def _trash_file(file, fcn):
    fcn(file)
    assert op.exists(file) is False


def _trash_multifile(files, fcn):
    fcn(files)
    assert any([op.exists(file) for file in files]) is False


def _file_not_found(dir, fcn):
    file = op.join(dir, "otherfile.txt")
    pytest.raises(OSError, fcn, file)


def _multi_byte_unicode(dir, fcn):
    single_file = op.join(dir, "😇.txt")
    _create_tree(single_file)
    assert op.exists(single_file) is True
    fcn(single_file)
    assert op.exists(single_file) is False
    files = [op.join(dir, "😇{}.txt".format(index)) for index in range(10)]
    [_create_tree(file) for file in files]
    assert all([op.exists(file) for file in files]) is True
    fcn(files)
    assert any([op.exists(file) for file in files]) is False


def test_trash_folder(testdir):
    _trash_folder(testdir, s2t)


def test_trash_file(testfile):
    _trash_file(testfile, s2t)


def test_trash_multifile(testfiles):
    _trash_multifile(testfiles, s2t)


def test_file_not_found(testdir):
    _file_not_found(testdir, s2t)


def test_trash_folder_modern(testdir):
    _trash_folder(testdir, s2t_modern)


def test_trash_file_modern(testfile):
    _trash_file(testfile, s2t_modern)


def test_trash_multifile_modern(testfiles):
    _trash_multifile(testfiles, s2t_modern)


def test_file_not_found_modern(testdir):
    _file_not_found(testdir, s2t_modern)


def test_multi_byte_unicode_modern(testdir):
    _multi_byte_unicode(testdir, s2t_modern)


def test_trash_folder_legacy(testdir):
    _trash_folder(testdir, s2t_legacy)


def test_trash_file_legacy(testfile):
    _trash_file(testfile, s2t_legacy)


def test_trash_multifile_legacy(testfiles):
    _trash_multifile(testfiles, s2t_legacy)


def test_file_not_found_legacy(testdir):
    _file_not_found(testdir, s2t_legacy)


def test_multi_byte_unicode_legacy(testdir):
    _multi_byte_unicode(testdir, s2t_legacy)


# Long path tests
@pytest.fixture
def longdir(tmp_path):
    dirname = "\\\\?\\" + str(tmp_path)
    name = "A" * 100
    yield op.join(dirname, name, name, name)
    try:
        shutil.rmtree(dirname, ignore_errors=True)
    except TypeError:
        pass


@pytest.fixture
def longfile(longdir):
    name = "A" * 100
    path = op.join(longdir, name + "{}.txt")
    file = path.format("")
    _create_tree(file)
    assert op.exists(file) is True
    yield file


@pytest.fixture
def longfiles(longdir):
    name = "A" * 100
    path = op.join(longdir, name + "{}.txt")
    files = [path.format(index) for index in range(10)]
    [_create_tree(file) for file in files]
    assert all([op.exists(file) for file in files]) is True
    yield files


# NOTE: both legacy and modern test "pass" on windows, however sometimes with the same path
# they do not actually recycle files but delete them.  Noticed this when testing with the
# recycle bin open, noticed later tests actually worked, modern version can actually detect
# when this happens but not stop it at this moment, and we need a way to verify it when testing.
def test_trash_long_file_modern(longfile):
    _trash_file(longfile, s2t_modern)


def test_trash_long_multifile_modern(longfiles):
    _trash_multifile(longfiles, s2t_modern)


#     @pytest.skipif(
#         op.splitdrive(os.getcwd())[0] != op.splitdrive(gettempdir())[0],
#         "Cannot trash long path from other drive",
#     )
#     def test_trash_long_folder_modern(self):
#         self._trash_folder(s2t_modern)


def test_trash_long_file_legacy(longfile):
    _trash_file(longfile, s2t_legacy)


def test_trash_long_multifile_legacy(longfiles):
    _trash_multifile(longfiles, s2t_legacy)


#     @pytest.skipif(
#         op.splitdrive(os.getcwd())[0] != op.splitdrive(gettempdir())[0],
#         "Cannot trash long path from other drive",
#     )
#     def test_trash_long_folder_legacy(self):
#         self._trash_folder(s2t_legacy)


def test_trash_nothing_legacy():
    try:
        s2t_legacy([])
    except Exception as ex:
        assert False, "Exception thrown when trashing nothing: {}".format(ex)


def test_trash_nothing_modern():
    try:
        s2t_modern([])
    except Exception as ex:
        assert False, "Exception thrown when trashing nothing: {}".format(ex)
