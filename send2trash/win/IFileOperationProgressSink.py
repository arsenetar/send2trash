# Sample implementation of IFileOperationProgressSink that just prints
# some basic info

import pythoncom
from win32com.shell import shell, shellcon
from win32com.server.policy import DesignatedWrapPolicy


class E_Fail(Exception):
    pass


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
        self.errors = []

    def PreDeleteItem(self, flags, item):
        # If TSF_DELETE_RECYCLE_IF_POSSIBLE is not set the file would not be moved to trash.
        # Usually the code would have to return S_OK or E_FAIL to signal an abort to the file sink,
        # however pywin32 doesn't use the return value of these callback methods [1], so we have to resort
        # to raising an exception as that does stop things.
        # [1] https://github.com/mhammond/pywin32/blob/1d29e4a4f317be9acbef9d5c5c5787269eacb040/com/win32com/src/PyGatewayBase.cpp#L757

        name = item.GetDisplayName(shellcon.SHGDN_FORPARSING)
        will_recycle = flags & shellcon.TSF_DELETE_RECYCLE_IF_POSSIBLE
        if not will_recycle:
            raise E_Fail(f"File would be deleted permanently: {name}")

        return None  # HR cannot be returned here

    def PostDeleteItem(self, flags, item, hr_delete, newly_created):
        if hr_delete < 0:
            name = item.GetDisplayName(shellcon.SHGDN_FORPARSING)
            self.errors.append((name, hr_delete))

        return None  # HR cannot be returned here


def create_sink():
    pysink = FileOperationProgressSink()
    return pysink, pythoncom.WrapObject(pysink, shell.IID_IFileOperationProgressSink)
