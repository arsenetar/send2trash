# Copyright 2017 Virgil Dupras

# This software is licensed under the "BSD" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.hardcoded.net/licenses/bsd_license

from platform import mac_ver
from sys import version_info

# If macOS is 11.0 or newer try to use the pyobjc version to get around #51
# NOTE: pyobjc only supports python >= 3.6
if version_info >= (3, 6) and int(mac_ver()[0].split(".", 1)[0]) >= 11:
    try:
        from .plat_osx_pyobjc import send2trash
    except ImportError:
        # Try to fall back to ctypes version, although likely problematic still
        from .plat_osx_ctypes import send2trash
else:
    # Just use the old version otherwise
    from .plat_osx_ctypes import send2trash  # noqa: F401
