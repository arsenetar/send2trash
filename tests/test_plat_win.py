# coding: utf-8
import os
import sys
import unittest
from os import path as op
from tempfile import gettempdir

from send2trash import send2trash as s2t


@unittest.skipIf(sys.platform != 'win32', 'Windows only')
class TestNormal(unittest.TestCase):
    def setUp(self):
        self.dirname = '\\\\?\\' + op.join(gettempdir(), 'python.send2trash')
        self.file = op.join(self.dirname, 'testfile.txt')
        self._create_tree(self.file)

    def tearDown(self):
        try:
            os.remove(self.dirname)
        except OSError:
            pass

    def _create_tree(self, path):
        dirname = op.dirname(path)
        if not op.isdir(dirname):
            os.makedirs(dirname)
        with open(path, 'w') as writer:
            writer.write('send2trash test')

    def test_trash_file(self):
        s2t(self.file)
        self.assertFalse(op.exists(self.file))

    def test_file_not_found(self):
        file = op.join(self.dirname, 'otherfile.txt')
        self.assertRaises(WindowsError, s2t, file)

@unittest.skipIf(sys.platform != 'win32', 'Windows only')
class TestLongPath(unittest.TestCase):
    def setUp(self):
        filename = 'A' * 100
        self.dirname = '\\\\?\\' + op.join(gettempdir(), filename)
        self.file = op.join(
            self.dirname,
            filename,
            filename,  # From there, the path is not trashable from Explorer
            filename,
            filename + '.txt')
        self._create_tree(self.file)

    def tearDown(self):
        try:
            os.remove(self.dirname)
        except OSError:
            pass

    def _create_tree(self, path):
        dirname = op.dirname(path)
        if not op.isdir(dirname):
            os.makedirs(dirname)
        with open(path, 'w') as writer:
            writer.write('Looong filename!')

    def test_trash_file(self):
        s2t(self.file)
        self.assertFalse(op.exists(self.file))

    @unittest.skipIf(
        op.splitdrive(os.getcwd())[0] != op.splitdrive(gettempdir())[0],
        'Cannot trash long path from other drive')
    def test_trash_folder(self):
        s2t(self.dirname)
        self.assertFalse(op.exists(self.dirname))
