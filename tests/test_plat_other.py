import codecs
import os
import sys
from os import path as op
from tempfile import mkdtemp, NamedTemporaryFile
import shutil
import stat
import uuid
from configparser import ConfigParser
import pytest
from send2trash import TrashPermissionError

if sys.platform == "win32":
    pytest.skip("Skipping non-windows tests", allow_module_level=True)
else:
    import send2trash.plat_other
    from send2trash.plat_other import send2trash as s2t
    from send2trash.plat_other import is_parent

INFO_SUFFIX = send2trash.plat_other.INFO_SUFFIX.decode()
HOMETRASH = send2trash.plat_other.HOMETRASH


@pytest.fixture(name="test_files")
def fixture_test_files():
    files = list(
        map(
            lambda index: NamedTemporaryFile(
                dir=op.expanduser("~"),
                prefix=f"send2trash_test{index}",
                delete=False,
            ),
            range(10),
        )
    )
    for file in files:
        file.close()
    assert all(op.exists(file.name) for file in files) is True
    yield files
    filenames = [op.basename(file.name) for file in files]
    for filename in filenames:
        os.remove(op.join(HOMETRASH, "files", filename))
        os.remove(op.join(HOMETRASH, "info", filename + INFO_SUFFIX))


def test_trash(test_file):
    s2t(test_file)
    assert op.exists(test_file) is False


def test_multitrash(test_files):
    file_names = [file.name for file in test_files]
    s2t(file_names)
    assert any(op.exists(filename) for filename in file_names) is False


def touch(path):
    with open(path, "a", encoding="utf-8"):
        os.utime(path, None)


def _filesys_enc():
    enc = sys.getfilesystemencoding()
    # Get canonical name of codec
    return codecs.lookup(enc).name


@pytest.fixture(name="gen_unicode_file")
def fixture_gen_unicode_file():
    name = "send2trash_tést1"
    file = op.join(op.expanduser(b"~"), name.encode("utf-8"))
    touch(file)
    assert op.exists(file) is True
    yield file
    # Cleanup trash files on supported platforms
    if sys.platform != "win32" and op.exists(op.join(HOMETRASH, "files", name)):
        os.remove(op.join(HOMETRASH, "files", name))
        os.remove(op.join(HOMETRASH, "info", name + INFO_SUFFIX))
    if op.exists(file):
        os.remove(file)


@pytest.mark.skipif(_filesys_enc() == "ascii", reason="Requires Unicode filesystem")
def test_trash_bytes(gen_unicode_file):
    s2t(gen_unicode_file)
    assert not op.exists(gen_unicode_file)


@pytest.mark.skipif(_filesys_enc() == "ascii", reason="Requires Unicode filesystem")
def test_trash_unicode(gen_unicode_file):
    s2t(gen_unicode_file.decode(sys.getfilesystemencoding()))
    assert not op.exists(gen_unicode_file)


class ExtVol:
    def __init__(self, path):
        self.trash_topdir = path
        self.trash_topdir_b = os.fsencode(self.trash_topdir)

        def s_getdev(path):
            st = os.lstat(path)
            if is_parent(self.trash_topdir, path):
                return "dev"
            return st.st_dev

        def s_ismount(path):
            if op.realpath(path) in (
                op.realpath(self.trash_topdir),
                op.realpath(self.trash_topdir_b),
            ):
                return True
            return old_ismount(path)

        self.old_ismount = old_ismount = op.ismount
        self.old_getdev = send2trash.plat_other.get_dev
        send2trash.plat_other.os.path.ismount = s_ismount
        send2trash.plat_other.get_dev = s_getdev

    def cleanup(self):
        send2trash.plat_other.get_dev = self.old_getdev
        send2trash.plat_other.os.path.ismount = self.old_ismount
        shutil.rmtree(self.trash_topdir)


@pytest.fixture(name="gen_ext_vol")
def fixture_gen_ext_vol():
    trash_topdir = mkdtemp(prefix="s2t")
    volume = ExtVol(trash_topdir)
    file_name = "test.txt"
    file_path = op.join(volume.trash_topdir, file_name)
    touch(file_path)
    assert op.exists(file_path) is True
    yield volume, file_name, file_path
    volume.cleanup()


def test_trash_topdir(gen_ext_vol):
    trash_dir = op.join(gen_ext_vol[0].trash_topdir, ".Trash")
    os.mkdir(trash_dir, 0o777 | stat.S_ISVTX)

    s2t(gen_ext_vol[2])
    assert op.exists(gen_ext_vol[2]) is False

    if sys.platform == "darwin":
        # On macOS, we can only verify the file was removed from original location
        pass
    else:
        # Others platforms we can test
        assert op.exists(op.join(trash_dir, str(os.getuid()), "files", gen_ext_vol[1])) is True
        assert (
            op.exists(
                op.join(
                    trash_dir,
                    str(os.getuid()),
                    "info",
                    gen_ext_vol[1] + INFO_SUFFIX,
                )
            )
            is True
        )

        cfg = ConfigParser()
        cfg.read(op.join(trash_dir, str(os.getuid()), "info", gen_ext_vol[1] + INFO_SUFFIX))
        assert (gen_ext_vol[1] == cfg.get("Trash Info", "Path", raw=True)) is True


def test_trash_topdir_fallback(gen_ext_vol):
    s2t(gen_ext_vol[2])
    assert op.exists(gen_ext_vol[2]) is False
    assert (
        op.exists(
            op.join(
                gen_ext_vol[0].trash_topdir,
                ".Trash-" + str(os.getuid()),
                "files",
                gen_ext_vol[1],
            )
        )
        is True
    )


def test_trash_topdir_failure(gen_ext_vol):
    os.chmod(gen_ext_vol[0].trash_topdir, 0o500)  # not writable to induce the exception
    pytest.raises(TrashPermissionError, s2t, [gen_ext_vol[2]])
    os.chmod(gen_ext_vol[0].trash_topdir, 0o700)  # writable to allow deletion


def test_trash_symlink(gen_ext_vol):
    # Generating a random uuid named path for symlink
    sl_dir = op.join(op.expanduser("~"), "s2t_" + str(uuid.uuid4()))
    os.mkdir(op.join(gen_ext_vol[0].trash_topdir, "subdir"), 0o700)
    file_path = op.join(gen_ext_vol[0].trash_topdir, "subdir", gen_ext_vol[1])
    touch(file_path)
    os.symlink(op.join(gen_ext_vol[0].trash_topdir, "subdir"), sl_dir)
    s2t(op.join(sl_dir, gen_ext_vol[1]))
    assert op.exists(file_path) is False
    assert (
        op.exists(
            op.join(
                gen_ext_vol[0].trash_topdir,
                ".Trash-" + str(os.getuid()),
                "files",
                gen_ext_vol[1],
            )
        )
        is True
    )
    os.remove(sl_dir)
