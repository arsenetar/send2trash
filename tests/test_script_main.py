# encoding: utf-8
import os
import unittest
from tempfile import NamedTemporaryFile
from os import path as op

from send2trash.__main__ import main as trash_main
from tests.test_plat_other import HOMETRASH


class TestMainTrash(unittest.TestCase):
    def setUp(self):
        self.file = NamedTemporaryFile(dir=op.expanduser('~'), prefix='send2trash_test', delete=False)

    def test_trash(self):
        trash_main(['-v', self.file.name])
        self.assertFalse(op.exists(self.file.name))

    def test_no_args(self):
        self.assertRaises(SystemExit, trash_main, [])
        self.assertRaises(SystemExit, trash_main, ['-v'])
        self.assertTrue(op.exists(self.file.name))
        trash_main([self.file.name])  # Trash the file so tearDown runs properly

    def tearDown(self):
        name = op.basename(self.file.name)
        os.remove(op.join(HOMETRASH, 'files', name))
        os.remove(op.join(HOMETRASH, 'info', name + '.trashinfo'))


if __name__ == '__main__':
    unittest.main()
