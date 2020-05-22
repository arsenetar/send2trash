# Copyright 2017 Virgil Dupras

# This software is licensed under the "BSD" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.hardcoded.net/licenses/bsd_license

from __future__ import unicode_literals
import os.path as op
from .compat import text_type
from platform import version
import pythoncom
import pywintypes
from win32com.shell import shell, shellcon


def send2trash(paths):
    if not isinstance(paths, list):
        paths = [paths]
    # convert data type
    paths = [
        text_type(path, "mbcs") if not isinstance(path, text_type) else path
        for path in paths
    ]
    # convert to full paths
    paths = [op.abspath(path) if not op.isabs(path) else path for path in paths]
    # remove the leading \\?\ if present
    paths = [path[4:] if path.startswith("\\\\?\\") else path for path in paths]
    # create instance of file operation object
    fileop = pythoncom.CoCreateInstance(
        shell.CLSID_FileOperation, None, pythoncom.CLSCTX_ALL, shell.IID_IFileOperation,
    )
    # default flags to use
    flags = (
        shellcon.FOF_NOCONFIRMATION
        | shellcon.FOF_NOERRORUI
        | shellcon.FOF_SILENT
        | shellcon.FOFX_EARLYFAILURE
    )
    # determine rest of the flags based on OS version
    # use newer recommended flags if available
    if int(version().split(".", 1)[0]) >= 8:
        flags |= (
            0x20000000  # FOFX_ADDUNDORECORD win 8+
            | 0x00080000  # FOFX_RECYCLEONDELETE win 8+
        )
    else:
        flags |= shellcon.FOF_ALLOWUNDO
    # set the flags
    fileop.SetOperationFlags(flags)
    # actually try to perform the operation, this section may throw a
    # pywintypes.com_error which does not seem to create as nice of an
    # error as OSError so wrapping with try to convert
    try:
        for path in paths:
            item = shell.SHCreateItemFromParsingName(path, None, shell.IID_IShellItem)
            fileop.DeleteItem(item)
        result = fileop.PerformOperations()
        aborted = fileop.GetAnyOperationsAborted()
        # if non-zero result or aborted throw an exception
        if result or aborted:
            raise OSError(None, None, paths, result)
    except pywintypes.com_error as error:
        # convert to standard OS error, allows other code to get a
        # normal errno
        raise OSError(None, error.strerror, path, error.hresult)
