import unittest
import os
from os import path as op
import send2trash.plat_other
from send2trash.plat_other import send2trash as s2t
from configparser import ConfigParser
from tempfile import mkdtemp, NamedTemporaryFile, mktemp
import shutil
import stat
# Could still use cleaning up. But no longer relies on ramfs.

def touch(path):
  with open(path, 'a'):
    os.utime(path, None)

class TestHomeTrash(unittest.TestCase):
  def setUp(self):
    self.file = NamedTemporaryFile(dir=op.expanduser("~"), 
      prefix='send2trash_test', delete=False)

  def test_trash(self):
    s2t(self.file.name)
    self.assertFalse(op.exists(self.file.name))

  def tearDown(self):
    hometrash = send2trash.plat_other.HOMETRASH
    name = op.basename(self.file.name)
    os.remove(op.join(hometrash, 'files', name))
    os.remove(op.join(hometrash, 'info', name+'.trashinfo'))

#
# Tests for files on some other volume than the user's home directory.
#
# What we need to stub:
# * plat_other.get_dev (to make sure the file will not be on the home dir dev)
# * os.path.ismount (to make our topdir look like a top dir)
#
class TestExtVol(unittest.TestCase):
  def setUp(self):
    self.trashTopdir = mkdtemp(prefix='s2t')
    self.fileName = 'test.txt'
    self.filePath = op.join(self.trashTopdir, self.fileName)
    touch(self.filePath)

    self.old_ismount = old_ismount = op.ismount
    self.old_getdev = send2trash.plat_other.get_dev
    def s_getdev(path):
      from send2trash.plat_other import is_parent
      st = os.lstat(path)
      if is_parent(self.trashTopdir, path):
        return 'dev'
      return st
    def s_ismount(path):
      if op.realpath(path) == op.realpath(self.trashTopdir):
        return True
      return old_ismount(path)

    send2trash.plat_other.os.path.ismount = s_ismount
    send2trash.plat_other.get_dev = s_getdev

  def tearDown(self):
    send2trash.plat_other.get_dev = self.old_getdev
    send2trash.plat_other.os.path.ismount = self.old_ismount
    shutil.rmtree(self.trashTopdir)

class TestTopdirTrash(TestExtVol):
  def setUp(self):
    TestExtVol.setUp(self)
    # Create a .Trash dir w/ a sticky bit
    self.trashDir = op.join(self.trashTopdir, '.Trash')
    os.mkdir(self.trashDir, 0o777|stat.S_ISVTX)

  def test_trash(self):
    s2t(self.filePath)
    self.assertFalse(op.exists(self.filePath))
    self.assertTrue(op.exists(op.join(self.trashDir, str(os.getuid()), 'files', self.fileName)))
    self.assertTrue(op.exists(op.join(self.trashDir, str(os.getuid()), 'info', self.fileName + '.trashinfo')))
    # info relative path (if another test is added, with the same fileName/Path,
    # then it gets renamed etc.)
    cfg = ConfigParser()
    cfg.read(op.join(self.trashDir, str(os.getuid()), 'info', self.fileName + '.trashinfo'))
    self.assertEqual(self.fileName, cfg.get('Trash Info', 'Path', 1))

# Test .Trash-UID
class TestTopdirTrashFallback(TestExtVol):
  def test_trash(self):
    touch(self.filePath)
    s2t(self.filePath)
    self.assertFalse(op.exists(self.filePath))
    self.assertTrue(op.exists(op.join(self.trashTopdir, '.Trash-' + str(os.getuid()), 'files', self.fileName)))

# Test failure
class TestTopdirFailure(TestExtVol):
  def setUp(self):
    TestExtVol.setUp(self)
    os.chmod(self.trashTopdir, 0o500) # not writable to induce the exception

  def test_trash(self):
    with self.assertRaises(OSError):
      s2t(self.filePath)
    self.assertTrue(op.exists(self.filePath))

  def tearDown(self):
    os.chmod(self.trashTopdir, 0o700) # writable to allow deletion
    TestExtVol.tearDown(self)

# Make sure it will find the mount point properly for a file in a symlinked path
class TestSymlink(TestExtVol):
  def setUp(self):
    TestExtVol.setUp(self)
    # Use mktemp (race conditioney but no symlink equivalent)
    # Since is_parent uses realpath(), and our getdev uses is_parent,
    # this should work
    self.slDir = mktemp(prefix='s2t', dir=op.expanduser('~'))
    
    os.mkdir(op.join(self.trashTopdir, 'subdir'), 0o700)
    self.filePath = op.join(self.trashTopdir, 'subdir', self.fileName)
    touch(self.filePath)
    os.symlink(op.join(self.trashTopdir, 'subdir'), self.slDir)

  def test_trash(self):
    s2t(op.join(self.slDir, self.fileName))
    self.assertFalse(op.exists(self.filePath))
    self.assertTrue(op.exists(op.join(self.trashTopdir, '.Trash-' + str(os.getuid()), 'files', self.fileName)))

  def tearDown(self):
    os.remove(self.slDir)
    TestExtVol.tearDown(self)

if __name__ == '__main__':
  unittest.main()
