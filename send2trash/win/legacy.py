# Copyright 2017 Virgil Dupras

# This software is licensed under the "BSD" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.hardcoded.net/licenses/bsd_license

import os
import os.path as op
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
from ctypes.wintypes import HWND, UINT, LPCWSTR, BOOL, BOOLEAN

from send2trash.exceptions import TrashPermissionError
from send2trash.util import preprocess_paths

kernel32 = windll.kernel32
GetShortPathNameW = kernel32.GetShortPathNameW

shell32 = windll.shell32
SHFileOperationW = shell32.SHFileOperationW

# Undocumented, but exported by ntdll since Windows 10 1607; missing before that, where long paths
# could not be enabled at all.
RtlAreLongPathsEnabled = getattr(windll.ntdll, "RtlAreLongPathsEnabled", None)
if RtlAreLongPathsEnabled is not None:
    RtlAreLongPathsEnabled.restype = BOOLEAN
    RtlAreLongPathsEnabled.argtypes = []


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


def convert_sh_file_opt_result(result):
    # map overlapping values from SHFileOpterationW to approximate standard windows errors
    # ref https://docs.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-shfileoperationw#return-value
    # ref https://docs.microsoft.com/en-us/windows/win32/debug/system-error-codes--0-499-
    results = {
        0x71: 0x50,  # DE_SAMEFILE -> ERROR_FILE_EXISTS
        0x72: 0x57,  # DE_MANYSRC1DEST -> ERROR_INVALID_PARAMETER
        0x73: 0x57,  # DE_DIFFDIR -> ERROR_INVALID_PARAMETER
        0x74: 0x57,  # DE_ROOTDIR -> ERROR_INVALID_PARAMETER
        0x75: 0x4C7,  # DE_OPCANCELLED -> ERROR_CANCELLED
        0x76: 0x57,  # DE_DESTSUBTREE -> ERROR_INVALID_PARAMETER
        0x78: 0x05,  # DE_ACCESSDENIEDSRC -> ERROR_ACCESS_DENIED
        0x79: 0x6F,  # DE_PATHTOODEEP -> ERROR_BUFFER_OVERFLOW
        0x7A: 0x57,  # DE_MANYDEST -> ERROR_INVALID_PARAMETER
        0x7C: 0xA1,  # DE_INVALIDFILES -> ERROR_BAD_PATHNAME
        0x7D: 0x57,  # DE_DESTSAMETREE -> ERROR_INVALID_PARAMETER
        0x7E: 0xB7,  # DE_FLDDESTISFILE -> ERROR_ALREADY_EXISTS
        0x80: 0xB7,  # DE_FILEDESTISFLD -> ERROR_ALREADY_EXISTS
        0x81: 0x6F,  # DE_FILENAMETOOLONG -> ERROR_BUFFER_OVERFLOW
        0x82: 0x13,  # DE_DEST_IS_CDROM -> ERROR_WRITE_PROTECT
        0x83: 0x13,  # DE_DEST_IS_DVD -> ERROR_WRITE_PROTECT
        0x84: 0x6F9,  # DE_DEST_IS_CDRECORD -> ERROR_UNRECOGNIZED_MEDIA
        0x85: 0xDF,  # DE_FILE_TOO_LARGE -> ERROR_FILE_TOO_LARGE
        0x86: 0x13,  # DE_SRC_IS_CDROM -> ERROR_WRITE_PROTECT
        0x87: 0x13,  # DE_SRC_IS_DVD -> ERROR_WRITE_PROTECT
        0x88: 0x6F9,  # DE_SRC_IS_CDRECORD -> ERROR_UNRECOGNIZED_MEDIA
        0xB7: 0x6F,  # DE_ERROR_MAX -> ERROR_BUFFER_OVERFLOW
        0x402: 0xA1,  # UNKNOWN -> ERROR_BAD_PATHNAME
        0x10000: 0x1D,  # ERRORONDEST -> ERROR_WRITE_FAULT
        0x10074: 0x57,  # DE_ROOTDIR | ERRORONDEST -> ERROR_INVALID_PARAMETER
    }

    return results.get(result, result)


def prefix_and_path(path):
    r"""Guess the long-path prefix based on the kind of *path*.
    Local paths (C:\folder\file.ext) and UNC names (\\server\folder\file.ext)
    are handled.

    Return a tuple of the long-path prefix and the prefixed path.
    """
    prefix, long_path = "\\\\?\\", path

    if not path.startswith(prefix):
        if path.startswith("\\\\"):
            # Likely a UNC name
            prefix = "\\\\?\\UNC"
            long_path = prefix + path[1:]
        else:
            # Likely a local path
            long_path = prefix + path
    elif path.startswith(prefix + "UNC\\"):
        # UNC name with long-path prefix
        prefix = "\\\\?\\UNC"

    return prefix, long_path


def get_awaited_path_from_prefix(prefix, path):
    """Guess the correct path to pass to the SHFileOperationW() call.
    The long-path prefix must be removed, so we should take care of
    different long-path prefixes.
    """
    if prefix == "\\\\?\\UNC":
        # We need to prepend a backslash for UNC names, as it was removed
        # in prefix_and_path().
        return "\\" + path[len(prefix) :]
    return path[len(prefix) :]


def get_short_path_name(long_name):
    prefix, long_path = prefix_and_path(long_name)
    buf_size = GetShortPathNameW(long_path, None, 0)
    # FIX: https://github.com/hsoft/send2trash/issues/31
    # If buffer size is zero, an error has occurred.
    if not buf_size:
        err_no = GetLastError()
        raise WindowsError(err_no, FormatError(err_no), long_path)
    output = create_unicode_buffer(buf_size)
    GetShortPathNameW(long_path, output, buf_size)
    return get_awaited_path_from_prefix(prefix, output.value)


MAX_PATH = 260


def utf16_len(path):
    # MAX_PATH counts UTF-16 code units, so a character outside the BMP takes two.
    # surrogatepass: a Windows file name may hold an unpaired surrogate.
    return len(path.encode("utf-16-le", "surrogatepass")) // 2


def long_paths_enabled():
    """Return whether this process is long-path aware.

    That takes both LongPathsEnabled=1 in the registry and a longPathAware manifest on the
    executable, and only then does SHFileOperationW delete a path of MAX_PATH or more permanently;
    otherwise it recycles such a path.
    """
    return RtlAreLongPathsEnabled is not None and bool(RtlAreLongPathsEnabled())


def too_long_to_recycle(path):
    """Return the first path at or under *path* that is MAX_PATH UTF-16 code units or longer, or None.

    SHFileOperationW deletes such a tree permanently instead of moving it to the Recycle Bin,
    and still reports success. Passing the top-level path as its 8.3 short name (the DOS-style
    alias such as PROGRA~1, see get_short_path_name) does not prevent it, because the shell
    still measures the long names.
    """
    prefix, long_path = prefix_and_path(path)
    top = get_awaited_path_from_prefix(prefix, long_path)
    if utf16_len(top) >= MAX_PATH:
        return top
    for root, dirs, files in os.walk(long_path):
        for name in dirs + files:
            full = get_awaited_path_from_prefix(prefix, op.join(root, name))
            if utf16_len(full) >= MAX_PATH:
                return full
    return None


def send2trash(paths):
    paths = preprocess_paths(paths)
    if not paths:
        return
    # convert data type
    paths = [str(path, "mbcs") if not isinstance(path, str) else path for path in paths]
    original_paths = paths
    # convert to full paths
    paths = [op.abspath(path) if not op.isabs(path) else path for path in paths]
    # SHFileOperationW offers no way to stop it from deleting permanently what it cannot recycle,
    # so refuse a path it would treat that way before calling it (see #28).
    if long_paths_enabled():
        for path in paths:
            if too_long_to_recycle(path) is not None:
                raise TrashPermissionError(path)
    # get short path to handle path length issues
    paths = [get_short_path_name(path) for path in paths]
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
    # Additional note on another issue here, unicode_buffer expects length in
    # bytes essentially, so having multi-byte characters causes issues if just
    # passing pythons string length.  Instead of dealing with this difference we
    # just create a buffer then a new one with an extra null.  Since the non-length
    # specified version apparently stops after the first null, join with a space first.
    buffer = create_unicode_buffer(" ".join(paths))
    # convert to a single string of null terminated paths
    path_string = "\0".join(paths)
    buffer = create_unicode_buffer(path_string, len(buffer) + 1)
    fileop.pFrom = LPCWSTR(addressof(buffer))
    fileop.pTo = None
    fileop.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_NOERRORUI | FOF_SILENT
    fileop.fAnyOperationsAborted = 0
    fileop.hNameMappings = 0
    fileop.lpszProgressTitle = None
    result = SHFileOperationW(byref(fileop))
    if result:
        error = convert_sh_file_opt_result(result)
        exception = WindowsError(None, FormatError(error), original_paths, error)
        exception.sh_file_operation_result = result
        raise exception
