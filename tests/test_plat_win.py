# coding: utf-8
import os
import shutil
import sys
import unittest
from os import path as op
from tempfile import gettempdir

from send2trash import send2trash as s2t

# import the two versions as well as the "automatic" version
if sys.platform == "win32":
    from send2trash.plat_win_modern import send2trash as s2t_modern
    from send2trash.plat_win_legacy import send2trash as s2t_legacy


@unittest.skipIf(sys.platform != "win32", "Windows only")
class TestNormal(unittest.TestCase):
    def setUp(self):
        self.dirname = "\\\\?\\" + op.join(gettempdir(), "python.send2trash")
        self.file = op.join(self.dirname, "testfile.txt")
        self._create_tree(self.file)
        self.files = [
            op.join(self.dirname, "testfile{}.txt".format(index)) for index in range(10)
        ]
        [self._create_tree(file) for file in self.files]

    def tearDown(self):
        shutil.rmtree(self.dirname, ignore_errors=True)

    def _create_tree(self, path):
        dirname = op.dirname(path)
        if not op.isdir(dirname):
            os.makedirs(dirname)
        with open(path, "w") as writer:
            writer.write("send2trash test")

    def _trash_file(self, fcn):
        fcn(self.file)
        self.assertFalse(op.exists(self.file))

    def _trash_multifile(self, fcn):
        fcn(self.files)
        self.assertFalse(any([op.exists(file) for file in self.files]))

    def _file_not_found(self, fcn):
        file = op.join(self.dirname, "otherfile.txt")
        self.assertRaises(WindowsError, fcn, file)

    def test_trash_file(self):
        self._trash_file(s2t)

    def test_trash_multifile(self):
        self._trash_multifile(s2t)

    def test_file_not_found(self):
        self._file_not_found(s2t)

    def test_trash_file_modern(self):
        self._trash_file(s2t_modern)

    def test_trash_multifile_modern(self):
        self._trash_multifile(s2t_modern)

    def test_file_not_found_modern(self):
        self._file_not_found(s2t_modern)

    def test_trash_file_legacy(self):
        self._trash_file(s2t_legacy)

    def test_trash_multifile_legacy(self):
        self._trash_multifile(s2t_legacy)

    def test_file_not_found_legacy(self):
        self._file_not_found(s2t_legacy)


@unittest.skipIf(sys.platform != "win32", "Windows only")
class TestLongPath(unittest.TestCase):
    def setUp(self):
        self.functions = {s2t: "auto", s2t_legacy: "legacy", s2t_modern: "modern"}
        filename = "A" * 100
        self.dirname = "\\\\?\\" + op.join(gettempdir(), filename)
        path = op.join(
            self.dirname,
            filename,
            filename,  # From there, the path is not trashable from Explorer
            filename,
            filename + "{}.txt",
        )
        self.file = path.format("")
        self._create_tree(self.file)
        self.files = [path.format(index) for index in range(10)]
        [self._create_tree(file) for file in self.files]

    def tearDown(self):
        shutil.rmtree(self.dirname, ignore_errors=True)

    def _create_tree(self, path):
        dirname = op.dirname(path)
        if not op.isdir(dirname):
            os.makedirs(dirname)
        with open(path, "w") as writer:
            writer.write("Looong filename!")

    def _trash_file(self, fcn):
        fcn(self.file)
        self.assertFalse(op.exists(self.file))

    def _trash_multifile(self, fcn):
        fcn(self.files)
        self.assertFalse(any([op.exists(file) for file in self.files]))

    def _trash_folder(self, fcn):
        fcn(self.dirname)
        self.assertFalse(op.exists(self.dirname))

    def test_trash_file(self):
        self._trash_file(s2t)

    def test_trash_multifile(self):
        self._trash_multifile(s2t)

    @unittest.skipIf(
        op.splitdrive(os.getcwd())[0] != op.splitdrive(gettempdir())[0],
        "Cannot trash long path from other drive",
    )
    def test_trash_folder(self):
        self._trash_folder(s2t)

    def test_trash_file_modern(self):
        self._trash_file(s2t_modern)

    def test_trash_multifile_modern(self):
        self._trash_multifile(s2t_modern)

    @unittest.skipIf(
        op.splitdrive(os.getcwd())[0] != op.splitdrive(gettempdir())[0],
        "Cannot trash long path from other drive",
    )
    def test_trash_folder_modern(self):
        self._trash_folder(s2t_modern)

    def test_trash_file_legacy(self):
        self._trash_file(s2t_legacy)

    def test_trash_multifile_legacy(self):
        self._trash_multifile(s2t_legacy)

    @unittest.skipIf(
        op.splitdrive(os.getcwd())[0] != op.splitdrive(gettempdir())[0],
        "Cannot trash long path from other drive",
    )
    def test_trash_folder_legacy(self):
        self._trash_folder(s2t_legacy)
