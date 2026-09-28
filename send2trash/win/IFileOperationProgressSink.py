# Sample implementation of IFileOperationProgressSink that just prints
# some basic info

import pythoncom
import winerror
from win32com.shell import shell, shellcon
from win32com.server.exception import COMException
from win32com.server.policy import DesignatedWrapPolicy


class FileOperationProgressSink(DesignatedWrapPolicy):
    _com_interfaces_ = [shell.IID_IFileOperationProgressSink]
    _public_methods_ = [
        "StartOperations",
        "FinishOperations",
        "PreRenameItem",
        "PostRenameItem",
        "PreMoveItem",
        "PostMoveItem",
        "PreCopyItem",
        "PostCopyItem",
        "PreDeleteItem",
        "PostDeleteItem",
        "PreNewItem",
        "PostNewItem",
        "UpdateProgress",
        "ResetTimer",
        "PauseTimer",
        "ResumeTimer",
    ]

    def __init__(self):
        self._wrap_(self)
        self.newItem = None

    def PreDeleteItem(self, flags, item):
        # Windows decides up front whether the item can go to the Recycle Bin. When it can't (network
        # drive, path of MAX_PATH characters or more, ...) it is deleted permanently instead, so abort.
        # pywin32 ignores the return value of this method, only raising stops the operation.
        if not flags & shellcon.TSF_DELETE_RECYCLE_IF_POSSIBLE:
            raise COMException(hresult=winerror.E_ABORT)

    def PostDeleteItem(self, flags, item, hr_delete, newly_created):
        if newly_created:
            self.newItem = newly_created.GetDisplayName(shellcon.SHGDN_FORPARSING)


def create_sink():
    return pythoncom.WrapObject(FileOperationProgressSink(), shell.IID_IFileOperationProgressSink)
