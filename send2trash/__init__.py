# Copyright 2013 Hardcoded Software (http://www.hardcoded.net)

# This software is licensed under the "BSD" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.hardcoded.net/licenses/bsd_license

import sys

from send2trash.exceptions import TrashPermissionError  # noqa: F401

if sys.version_info[0] < 3:
    raise RuntimeError("send2trash is only compatible with Python 3 and above (use versions <= 1.8.3 for python 2).")

if sys.platform == "darwin":
    from send2trash.mac import send2trash
elif sys.platform == "win32":
    from send2trash.win import send2trash
else:
    send2trash = None
    try:
        from send2trash.plat_kio import is_available as _kio_is_available
        from send2trash.plat_kio import send2trash as _send2trash
    except ImportError:
        _send2trash = None
    else:
        if _kio_is_available():
            send2trash = _send2trash

    if send2trash is None:
        try:
            # If we can use gio, let's use it
            from send2trash.plat_gio import send2trash as _send2trash
        except ImportError:
            # Oh well, let's fallback to our own Freedesktop trash implementation
            from send2trash.plat_other import send2trash as _send2trash  # noqa: F401
        send2trash = _send2trash
