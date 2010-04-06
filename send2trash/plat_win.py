import os.path as op
import _send2trash_win

def send2trash(path):
    if not isinstance(path, unicode):
        path = unicode(path, 'mbcs')
    if not op.isabs(path):
        path = op.abspath(path)
    _send2trash_win.send(path)
