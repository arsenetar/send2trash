from __future__ import unicode_literals
import sys
import os
import os.path as op

TRASH_PATH = op.expanduser('~/.Trash')

# XXX Make this work on external volumes

def send2trash(path):
    if not isinstance(path, unicode):
        path = unicode(path, sys.getfilesystemencoding())
    filename = op.basename(path)
    destpath = op.join(TRASH_PATH, filename)
    counter = 0
    while op.exists(destpath):
        counter += 1
        base_name, ext = op.splitext(filename)
        new_filename = '{0} {1}{2}'.format(base_name, counter, ext)
        destpath = op.join(TRASH_PATH, new_filename)
    os.rename(path, destpath)
