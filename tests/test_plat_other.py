# encoding: utf-8
import pytest
import codecs
import os
import sys
from os import path as op
from send2trash.compat import PY3
from send2trash import TrashPermissionError

try:
    from configparser import ConfigParser
except ImportError:
    # py2
    from ConfigParser import ConfigParser  # noqa: F401

from tempfile import mkdtemp, NamedTemporaryFile, mktemp
import shutil
import stat

if sys.platform != "win32":
    import send2trash.plat_other
    from send2trash.plat_other import send2trash as s2t

    HOMETRASH = send2trash.plat_other.HOMETRASH
else:
    pytest.skip("Skipping non-windows tests", allow_module_level=True)


@pytest.fixture
def testfile():
    file = NamedTemporaryFile(dir=op.expanduser("~"), prefix="send2trash_test", delete=False)
    file.close()
    assert op.exists(file.name) is True
    yield file
    # Cleanup trash files on supported platforms
    if sys.platform != "win32":
        name = op.basename(file.name)
        # Remove trash files if they exist
        if op.exists(op.join(HOMETRASH, "files", name)):
            os.remove(op.join(HOMETRASH, "files", name))
            os.remove(op.join(HOMETRASH, "info", name + ".trashinfo"))
    if op.exists(file.name):
        os.remove(file.name)


@pytest.fixture
def testfiles():
    files = list(
        map(
            lambda index: NamedTemporaryFile(
                dir=op.expanduser("~"), prefix="send2trash_test{}".format(index), delete=False,
            ),
            range(10),
        )
    )
    [file.close() for file in files]
    assert all([op.exists(file.name) for file in files]) is True
    yield files
    filenames = [op.basename(file.name) for file in files]
    [os.remove(op.join(HOMETRASH, "files", filename)) for filename in filenames]
    [os.remove(op.join(HOMETRASH, "info", filename + ".trashinfo")) for filename in filenames]


def test_trash(testfile):
    s2t(testfile.name)
    assert op.exists(testfile.name) is False


def test_multitrash(testfiles):
    filenames = [file.name for file in testfiles]
    s2t(filenames)
    assert any([op.exists(filename) for filename in filenames]) is False


def touch(path):
    with open(path, "a"):
        os.utime(path, None)


def _filesys_enc():
    enc = sys.getfilesystemencoding()
    # Get canonical name of codec
    return codecs.lookup(enc).name


@pytest.fixture
def testUnicodefile():
    name = u"send2trash_tést1"
    file = op.join(op.expanduser(b"~"), name.encode("utf-8"))
    touch(file)
    assert op.exists(file) is True
    yield file
    # Cleanup trash files on supported platforms
    if sys.platform != "win32":
        # Remove trash files if they exist
        if op.exists(op.join(HOMETRASH, "files", name)):
            os.remove(op.join(HOMETRASH, "files", name))
            os.remove(op.join(HOMETRASH, "info", name + ".trashinfo"))
    if op.exists(file):
        os.remove(file)


@pytest.mark.skipif(_filesys_enc() == "ascii", reason="Requires Unicode filesystem")
def test_trash_bytes(testUnicodefile):
    s2t(testUnicodefile)
    assert not op.exists(testUnicodefile)


@pytest.mark.skipif(_filesys_enc() == "ascii", reason="Requires Unicode filesystem")
def test_trash_unicode(testUnicodefile):
    s2t(testUnicodefile.decode(sys.getfilesystemencoding()))
    assert not op.exists(testUnicodefile)


class ExtVol:
    def __init__(self, path):
        self.trashTopdir = path
        if PY3:
            self.trashTopdir_b = os.fsencode(self.trashTopdir)
        else:
            self.trashTopdir_b = self.trashTopdir

        def s_getdev(path):
            from send2trash.plat_other import is_parent

            st = os.lstat(path)
            if is_parent(self.trashTopdir, path):
                return "dev"
            return st.st_dev

        def s_ismount(path):
            if op.realpath(path) in (op.realpath(self.trashTopdir), op.realpath(self.trashTopdir_b),):
                return True
            return old_ismount(path)

        self.old_ismount = old_ismount = op.ismount
        self.old_getdev = send2trash.plat_other.get_dev
        send2trash.plat_other.os.path.ismount = s_ismount
        send2trash.plat_other.get_dev = s_getdev

    def cleanup(self):
        send2trash.plat_other.get_dev = self.old_getdev
        send2trash.plat_other.os.path.ismount = self.old_ismount
        shutil.rmtree(self.trashTopdir)


@pytest.fixture
def testExtVol():
    trashTopdir = mkdtemp(prefix="s2t")
    volume = ExtVol(trashTopdir)
    fileName = "test.txt"
    filePath = op.join(volume.trashTopdir, fileName)
    touch(filePath)
    assert op.exists(filePath) is True
    yield volume, fileName, filePath
    volume.cleanup()


def test_trash_topdir(testExtVol):
    trashDir = op.join(testExtVol[0].trashTopdir, ".Trash")
    os.mkdir(trashDir, 0o777 | stat.S_ISVTX)

    s2t(testExtVol[2])
    assert op.exists(testExtVol[2]) is False
    assert op.exists(op.join(trashDir, str(os.getuid()), "files", testExtVol[1])) is True
    assert op.exists(op.join(trashDir, str(os.getuid()), "info", testExtVol[1] + ".trashinfo",)) is True
    # info relative path (if another test is added, with the same fileName/Path,
    # then it gets renamed etc.)
    cfg = ConfigParser()
    cfg.read(op.join(trashDir, str(os.getuid()), "info", testExtVol[1] + ".trashinfo"))
    assert (testExtVol[1] == cfg.get("Trash Info", "Path", raw=True)) is True


def test_trash_topdir_fallback(testExtVol):
    s2t(testExtVol[2])
    assert op.exists(testExtVol[2]) is False
    assert op.exists(op.join(testExtVol[0].trashTopdir, ".Trash-" + str(os.getuid()), "files", testExtVol[1],)) is True


def test_trash_topdir_failure(testExtVol):
    os.chmod(testExtVol[0].trashTopdir, 0o500)  # not writable to induce the exception
    pytest.raises(TrashPermissionError, s2t, [testExtVol[2]])
    os.chmod(testExtVol[0].trashTopdir, 0o700)  # writable to allow deletion


def test_trash_symlink(testExtVol):
    # Use mktemp (race conditioney but no symlink equivalent)
    # Since is_parent uses realpath(), and our getdev uses is_parent,
    # this should work
    slDir = mktemp(prefix="s2t", dir=op.expanduser("~"))
    os.mkdir(op.join(testExtVol[0].trashTopdir, "subdir"), 0o700)
    filePath = op.join(testExtVol[0].trashTopdir, "subdir", testExtVol[1])
    touch(filePath)
    os.symlink(op.join(testExtVol[0].trashTopdir, "subdir"), slDir)
    s2t(op.join(slDir, testExtVol[1]))
    assert op.exists(filePath) is False
    assert op.exists(op.join(testExtVol[0].trashTopdir, ".Trash-" + str(os.getuid()), "files", testExtVol[1],)) is True
    os.remove(slDir)
