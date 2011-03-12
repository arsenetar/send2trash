import unittest
import os
from os import path as op
from send2trash.plat_other import send2trash
from configparser import ConfigParser

# XXX Although this unittest is better than no unit test at all, it would be better to mock
# os.path.mountpoint() rather than going through ramfs (and requiring admin rights).

#
# Warning: This test will shit up your Trash folder with test.txt files.
#
class TestHomeTrash(unittest.TestCase):
  def setUp(self):
    self.filePath = op.expanduser("~/test.txt")

  def test_trash(self):
    os.system('touch ' + self.filePath)
    send2trash(self.filePath)
    self.assertFalse(op.exists(self.filePath))

#
# Following cases use sudo, require ramfs
#
class TestRamFs(unittest.TestCase):
  def setUp(self):
    # Create a ramfs thingy.
    self.trashFolder = '/tmp/trashtest'
    os.system('sudo mkdir ' + self.trashFolder)
    os.system('sudo mount -t ramfs none ' + self.trashFolder)
    self.fileName = 'test.txt'
    self.filePath = op.join(self.trashFolder, self.fileName)

  def tearDown(self):
    os.system('sudo umount ' + self.trashFolder)
    os.system('sudo rmdir ' + self.trashFolder)

class TestTopdirTrash(TestRamFs):
  def setUp(self):
    TestRamFs.setUp(self)
    # Create a .Trash dir w/ a sticky bit
    os.system('sudo chmod a+w ' + self.trashFolder)
    os.system('sudo mkdir ' + op.join(self.trashFolder, '.Trash'))
    os.system('sudo chmod a+wt ' + op.join(self.trashFolder, '.Trash'))

  def test_trash(self):
    os.system('touch ' + self.filePath)
    send2trash(self.filePath)
    self.assertFalse(op.exists(self.filePath))
    self.assertTrue(op.exists(op.join(self.trashFolder, '.Trash', str(os.getuid()), 'files', self.fileName)))
    self.assertTrue(op.exists(op.join(self.trashFolder, '.Trash', str(os.getuid()), 'info', self.fileName + '.trashinfo')))
    # info relative path (if another test is added, with the same fileName/Path,
    # then it gets renamed etc.)
    cfg = ConfigParser()
    cfg.read(op.join(self.trashFolder, '.Trash', str(os.getuid()), 'info', self.fileName + '.trashinfo'))
    self.assertEqual(self.fileName, cfg.get('Trash Info', 'Path', 1))

# Test .Trash-UID
class TestTopdirTrashFallback(TestRamFs):
  def setUp(self):
    TestRamFs.setUp(self)
    # DONT Create a .Trash dir, but make sure the topdir is writable for uid dir
    os.system('sudo chmod a+w ' + self.trashFolder)

  def test_trash(self):
    os.system('touch ' + self.filePath)
    send2trash(self.filePath)
    self.assertFalse(op.exists(self.filePath))
    self.assertTrue(op.exists(op.join(self.trashFolder, '.Trash-' + str(os.getuid()), 'files', self.fileName)))

# Test failure
class TestTopdirFailure(TestRamFs):
  def test_trash(self):
    # a file to call our own
    os.system('sudo chmod o+w ' + self.trashFolder)
    os.system('touch ' + self.filePath)
    os.system('sudo chmod o-w ' + self.trashFolder)

    with self.assertRaises(OSError):
      send2trash(self.filePath)
    self.assertTrue(op.exists(self.filePath))

if __name__ == '__main__':
  unittest.main()
