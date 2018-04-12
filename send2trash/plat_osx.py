# Copyright 2017 Virgil Dupras

# This software is licensed under the "BSD" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.hardcoded.net/licenses/bsd_license

from __future__ import unicode_literals

from ctypes import cdll, byref, Structure, c_char, c_char_p, c_void_p, c_int64, sizeof
from ctypes.util import find_library

from .compat import binary_type

Foundation = cdll.LoadLibrary(find_library('Foundation'))
CoreServices = cdll.LoadLibrary(find_library('CoreServices'))
objc = cdll.LoadLibrary(find_library('objc'))

GetMacOSStatusCommentString = Foundation.GetMacOSStatusCommentString
GetMacOSStatusCommentString.restype = c_char_p
FSPathMakeRefWithOptions = CoreServices.FSPathMakeRefWithOptions
FSMoveObjectToTrashSync = CoreServices.FSMoveObjectToTrashSync
AEGetParamDesc = CoreServices.AEGetParamDesc
AESendMessage = CoreServices.AESendMessage

kFSPathMakeRefDefaultOptions = 0
kFSPathMakeRefDoNotFollowLeafSymlink = 0x01

kFSFileOperationDefaultOptions = 0
kFSFileOperationOverwrite = 0x01
kFSFileOperationSkipSourcePermissionErrors = 0x02
kFSFileOperationDoNotMoveAcrossVolumes = 0x04
kFSFileOperationSkipPreflight = 0x08

class FSRef(Structure):
    _fields_ = [('hidden', c_char * 80)]

def check_op_result(op_result):
    if op_result:
        msg = GetMacOSStatusCommentString(op_result).decode('utf-8')
        raise OSError(msg)

def send2trash(path, with_put_back=False):
    if not isinstance(path, binary_type):
        path = path.encode('utf-8')
    _with_put_back(path) if with_put_back else _normally(path)

def _normally(path):
    fp = FSRef()
    opts = kFSPathMakeRefDoNotFollowLeafSymlink
    op_result = FSPathMakeRefWithOptions(path, opts, byref(fp), None)
    check_op_result(op_result)
    opts = kFSFileOperationDefaultOptions
    op_result = FSMoveObjectToTrashSync(byref(fp), None, opts)
    check_op_result(op_result)

# Everything below here is required for getting the "put back" feature
# in the macOS trash - we attempt to ask Finder the trash the file for us.

objc.objc_getClass.restype = c_void_p
objc.sel_registerName.restype = c_void_p
objc.objc_msgSend.restype = c_void_p
objc.objc_msgSend.argtypes = [c_void_p, c_void_p]

_msg = objc.objc_msgSend
_cls = objc.objc_getClass
_sel = objc.sel_registerName

kAEWaitReply = 0x3
kAnyTransactionID = 0
kAEDefaultTimeout = -1
kAutoGenerateReturnID = -1
NSUTF8StringEncoding = 0x4

# TODO: this is probably incorrect/or changes depending on arch, etc
typeKernelProcessID = 0x6b706964

# TODO: not sure exactly what these should be
keyDirectObject = '----'
typeWildCard = '****'

class AEDataStorage(Structure):
    _fields_ = []

# AppleEvent seems to be an alias of AEDesc
class AEDesc(Structure):
    # DescType is an unsigned int ?
    # AEDataStorage is something else ?
    _fields_ = [('descriptorType', c_int64), ('dataHandle', AEDataStorage)]

# This was inspired by https://github.com/ali-rantakari/trash.
# See https://github.com/ali-rantakari/trash/blob/master/trash.m#L263-L341
# and also https://stackoverflow.com/a/1490644/5552584.
def _with_put_back(path):
    # Create an autorelease pool.
    NSAutoreleasePool = _cls('NSAutoreleasePool')
    pool = _msg(NSAutoreleasePool, _sel('alloc'))
    pool = _msg(pool, _sel('init'))

    try:
        # Generate list descriptor containing the file URL
        NSAppleEventDescriptor = _cls('NSAppleEventDescriptor')
        url_list_descr = _msg(NSAppleEventDescriptor, _sel('listDescriptor'))
        url = _msg(_cls('NSURL'), _sel('fileURLWithPath'), path)
        url_str = _msg(url, _sel('absoluteString'))
        data = _msg(url_str, _sel('dataUsingEncoding:'), NSUTF8StringEncoding)
        descr = _msg(NSAppleEventDescriptor,
            _sel('descriptorWithDescriptorType:'), 'furl',
            _sel('data:'), data)
        _msg(url_list_descr,
            _sel('insertDescriptor:'), descr,
            _sel('atIndex:'), 1)

        # Generate the 'top level' "delete" descriptor
        finder_pid = _get_finder_pid()
        target_descr = _msg(NSAppleEventDescriptor,
            _sel('descriptorWithDescriptorType:'), typeKernelProcessID,
            _sel('bytes:'), byref(finder_pid),
            _sel('length:'), sizeof(finder_pid))
        descriptor = _msg(NSAppleEventDescriptor,
            _sel('appleEventWithEventClass:'), 'core',
            _sel('eventID:'), 'delo',
            _sel('targetDescriptor:'), target_descr,
            _sel('returnID:'), kAutoGenerateReturnID,
            _sel('transactionID:'), kAnyTransactionID)

        # add the list of file URLs as argument
        _msg(descriptor,
            _sel('setDescriptor:'), url_list_descr,
            _sel('forKeyword:'), '----')

        # send the Apple Event synchronously
        reply_event = AEDesc()
        op_result = AESendMessage(_msg(descriptor, _sel('asDesc')),
            byref(reply_event), kAEWaitReply, kAEDefaultTimeout)
        check_op_result(op_result)

        # check reply in order to determine return value
        reply_ae_descr = AEDesc()
        op_result = AEGetParamDesc(byref(reply_event), keyDirectObject,
            typeWildCard, byref(reply_ae_descr))
        check_op_result(op_result)

        reply_descr = _msg(_msg(_msg(NSAppleEventDescriptor, _sel('alloc')),
            _sel('initWithAEDescNoCopy:'), byref(reply_ae_descr)), _sel('autorelease'))

        if _msg(reply_descr, _sel('numberOfItems')) == 0:
            raise Exception('file could not be trashed')
    finally:
        _msg(pool, _sel('release'))

def _get_finder_pid():
    import subprocess
    child = subprocess.Popen(['pgrep', '-f', 'Finder'],
        stdout=subprocess.PIPE, shell=False)
    response = child.communicate()[0]
    # TODO: assumed that pid_t is a c_int64 (should depend on arch)
    return c_int64(int(response.split()[0]))
