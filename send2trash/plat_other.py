# Copyright 2010 Hardcoded Software (http://www.hardcoded.net)

# This software is licensed under the "BSD" License as described in the "LICENSE" file, 
# which should be included with this package. The terms are also available at 
# http://www.hardcoded.net/licenses/bsd_license

from __future__ import unicode_literals
import sys
import os
import os.path as op
import logging

CANDIDATES = [
    '~/.local/share/Trash/files',
    '~/.Trash',
]

for candidate in CANDIDATES:
    candidate_path = op.expanduser(candidate)
    if op.exists(candidate_path):
        TRASH_PATH = candidate_path
        break
else:
    logging.warning("Can't find path for Trash")
    TRASH_PATH = op.expanduser('~/.Trash')

EXTERNAL_CANDIDATES = [
    '.Trash-1000/files',
    '.Trash/files',
    '.Trash-1000',
    '.Trash',
]

def find_mount_point(path):
    # Even if something's wrong, "/" is a mount point, so the loop will exit.
    while not op.ismount(path):
        path = op.join(*op.split(path)[:-1])
    return path

def find_ext_volume_trash(volume_root):
    for candidate in EXTERNAL_CANDIDATES:
        candidate_path = op.join(volume_root, candidate)
        if op.exists(candidate_path):
            return candidate_path
    else:
        # Something's wrong here. Screw that, just create a .Trash folder
        trash_path = op.join(volume_root, '.Trash')
        os.mkdir(trash_path)
        return trash_path

def move_without_conflict(src, dst):
    filename = op.basename(src)
    destpath = op.join(dst, filename)
    counter = 0
    while op.exists(destpath):
        counter += 1
        base_name, ext = op.splitext(filename)
        new_filename = '{0} {1}{2}'.format(base_name, counter, ext)
        destpath = op.join(TRASH_PATH, new_filename)
    os.rename(src, destpath)

def send2trash(path):
    if not isinstance(path, unicode):
        path = unicode(path, sys.getfilesystemencoding())
    try:
        move_without_conflict(path, TRASH_PATH)
    except OSError:
        # We're probably on an external volume
        mount_point = find_mount_point(path)
        dest_trash = find_ext_volume_trash(mount_point)
        move_without_conflict(path, dest_trash)
