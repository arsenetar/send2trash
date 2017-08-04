# encoding: utf-8
import codecs
import unittest
import os
from os import path as op
import send2trash.plat_other
from send2trash.plat_other import send2trash as s2t
from send2trash.compat import PY3
from configparser import ConfigParser
from tempfile import mkdtemp, NamedTemporaryFile, mktemp
import shutil
import stat
import sys
# Could still use cleaning up. But no longer relies on ramfs.

HOMETRASH = send2trash.plat_other.HOMETRASH

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
    name = op.basename(self.file.name)
    os.remove(op.join(HOMETRASH, 'files', name))
    os.remove(op.join(HOMETRASH, 'info', name+'.trashinfo'))

def _filesys_enc():
  enc = sys.getfilesystemencoding()
  # Get canonical name of codec
  return codecs.lookup(enc).name

@unittest.skipIf(_filesys_enc() == 'ascii', 'ASCII filesystem')
class TestUnicodeTrash(unittest.TestCase):
  def setUp(self):
    self.name = u'send2trash_tést1'
    self.file = op.join(op.expanduser(b'~'), self.name.encode('utf-8'))
    touch(self.file)

  def test_trash_bytes(self):
    s2t(self.file)
    assert not op.exists(self.file)

  def test_trash_unicode(self):
    s2t(self.file.decode(sys.getfilesystemencoding()))
    assert not op.exists(self.file)

  def tearDown(self):
    if op.exists(self.file):
      os.remove(self.file)

    trash_file = op.join(HOMETRASH, 'files', self.name)
    if op.exists(trash_file):
      os.remove(trash_file)
      os.remove(op.join(HOMETRASH, 'info', self.name+'.trashinfo'))

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
    if PY3:
      trashTopdir_b = os.fsencode(self.trashTopdir)
    else:
      trashTopdir_b = self.trashTopdir
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
      return st.st_dev
    def s_ismount(path):
      if op.realpath(path) in \
              (op.realpath(self.trashTopdir), op.realpath(trashTopdir_b)):
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
    self.assertEqual(self.fileName, cfg.get('Trash Info', 'Path', raw=True))

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
