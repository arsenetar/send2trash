# Copyright 2017 Virgil Dupras

# This software is licensed under the "BSD" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.hardcoded.net/licenses/bsd_license

from __future__ import unicode_literals
import os.path as op
from .compat import text_type

try:
    # Attempt to use pywin32 to use IFileOperation
    import pythoncom
    import pywintypes
    from win32com.shell import shell, shellcon
    from platform import version

    def send2trash(path):
        if not isinstance(path, list):
            path = [path]
        # convert data type
        path = [
            text_type(item, "mbcs") if not isinstance(item, text_type) else item
            for item in path
        ]
        # convert to full paths
        path = [op.abspath(item) if not op.isabs(item) else item for item in path]
        # remove the leading \\?\ if present
        path = [item[4:] for item in path if item.startswith("\\\\?\\")]
        # create instance of file operation object
        fileop = pythoncom.CoCreateInstance(
            shell.CLSID_FileOperation,
            None,
            pythoncom.CLSCTX_ALL,
            shell.IID_IFileOperation,
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
        if int(version().split(".", 1)[0]) >= 8 and False:
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
            for itemPath in path:
                item = shell.SHCreateItemFromParsingName(
                    itemPath, None, shell.IID_IShellItem
                )
                fileop.DeleteItem(item)
            result = fileop.PerformOperations()
            aborted = fileop.GetAnyOperationsAborted()
            # if non-zero result or aborted throw an exception
            if result or aborted:
                raise OSError(None, None, path, result)
        except pywintypes.com_error as error:
            # convert to standard OS error, allows other code to get a
            # normal errno
            raise OSError(None, error.strerror, path, error.hresult)


except ImportError:
    from ctypes import (
        windll,
        Structure,
        byref,
        c_uint,
        create_unicode_buffer,
        addressof,
        GetLastError,
        FormatError,
    )
    from ctypes.wintypes import HWND, UINT, LPCWSTR, BOOL

    kernel32 = windll.kernel32
    GetShortPathNameW = kernel32.GetShortPathNameW

    shell32 = windll.shell32
    SHFileOperationW = shell32.SHFileOperationW

    class SHFILEOPSTRUCTW(Structure):
        _fields_ = [
            ("hwnd", HWND),
            ("wFunc", UINT),
            ("pFrom", LPCWSTR),
            ("pTo", LPCWSTR),
            ("fFlags", c_uint),
            ("fAnyOperationsAborted", BOOL),
            ("hNameMappings", c_uint),
            ("lpszProgressTitle", LPCWSTR),
        ]

    FO_MOVE = 1
    FO_COPY = 2
    FO_DELETE = 3
    FO_RENAME = 4

    FOF_MULTIDESTFILES = 1
    FOF_SILENT = 4
    FOF_NOCONFIRMATION = 16
    FOF_ALLOWUNDO = 64
    FOF_NOERRORUI = 1024

    def get_short_path_name(long_name):
        if not long_name.startswith("\\\\?\\"):
            long_name = "\\\\?\\" + long_name
        buf_size = GetShortPathNameW(long_name, None, 0)
        # FIX: https://github.com/hsoft/send2trash/issues/31
        # If buffer size is zero, an error has occurred.
        if not buf_size:
            err_no = GetLastError()
            raise WindowsError(err_no, FormatError(err_no), long_name[4:])
        output = create_unicode_buffer(buf_size)
        GetShortPathNameW(long_name, output, buf_size)
        return output.value[4:]  # Remove '\\?\' for SHFileOperationW

    def send2trash(path):
        if not isinstance(path, text_type):
            path = text_type(path, "mbcs")
        if not op.isabs(path):
            path = op.abspath(path)
        path = get_short_path_name(path)
        fileop = SHFILEOPSTRUCTW()
        fileop.hwnd = 0
        fileop.wFunc = FO_DELETE
        # FIX: https://github.com/hsoft/send2trash/issues/17
        # Starting in python 3.6.3 it is no longer possible to use:
        # LPCWSTR(path + '\0') directly as embedded null characters are no longer
        # allowed in strings
        # Workaround
        #  - create buffer of c_wchar[] (LPCWSTR is based on this type)
        #  - buffer is two c_wchar characters longer (double null terminator)
        #  - cast the address of the buffer to a LPCWSTR
        # NOTE: based on how python allocates memory for these types they should
        # always be zero, if this is ever not true we can go back to explicitly
        # setting the last two characters to null using buffer[index] = '\0'.
        buffer = create_unicode_buffer(path, len(path) + 2)
        fileop.pFrom = LPCWSTR(addressof(buffer))
        fileop.pTo = None
        fileop.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_NOERRORUI | FOF_SILENT
        fileop.fAnyOperationsAborted = 0
        fileop.hNameMappings = 0
        fileop.lpszProgressTitle = None
        result = SHFileOperationW(byref(fileop))
        if result:
            raise WindowsError(result, FormatError(result), path)
