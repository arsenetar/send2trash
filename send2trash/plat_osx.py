import _send2trash_osx

def send2trash(path):
    if not isinstance(path, unicode):
        path = unicode(path, 'utf-8')
    _send2trash_osx.send(path)
