# Copyright 2010 Hardcoded Software (http://www.hardcoded.net)

# This software is licensed under the "BSD" License as described in the "LICENSE" file, 
# which should be included with this package. The terms are also available at 
# http://www.hardcoded.net/licenses/bsd_license

import _send2trash_osx

def send2trash(path):
    if not isinstance(path, unicode):
        path = unicode(path, 'utf-8')
    _send2trash_osx.send(path)
