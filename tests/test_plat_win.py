# coding: utf-8
import os
import sys
import unittest
from os import path as op
from tempfile import gettempdir

from send2trash import send2trash as s2t


@unittest.skipIf(sys.platform != 'win32', 'Windows only')
class TestLongPath(unittest.TestCase):
    def setUp(self):
        filename = 'A' * 100
        self.dirname = '\\\\?\\' + os.path.join(gettempdir(), filename)
        self.file = os.path.join(
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
        dirname = os.path.dirname(path)
        if not os.path.isdir(dirname):
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
