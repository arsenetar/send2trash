#define PY_SSIZE_T_CLEAN
#include "Python.h"

#define WINDOWS_LEAN_AND_MEAN
#include "windows.h"
#include "shlobj.h"

/* WARNING: If the filepath is not fully qualify, Windows deletes the file
   rather than sending it to trash. 
 */

static PyObject* trash_win_send(PyObject *self, PyObject *args)
{
    SHFILEOPSTRUCTW op;
    PyObject *filepath;
    Py_ssize_t len, cpysize;
    WCHAR filechars[MAX_PATH+1];
    int r;
    
    if (!PyArg_ParseTuple(args, "O", &filepath)) {
        return NULL;
    }
    
    if (!PyUnicode_Check(filepath)) {
        PyErr_SetString(PyExc_TypeError, "Unicode filename required");
        return NULL;
    }
    
    len = PyUnicode_GET_SIZE(filepath);
    /* +2 because we are going to add two null chars at the end */
    cpysize = sizeof(WCHAR) * (len + 2);
    memcpy(filechars, PyUnicode_AsUnicode(filepath), cpysize);
    filechars[len] = '\0';
    filechars[len+1] = '\0';

    op.hwnd = 0;
    op.wFunc = FO_DELETE;
    op.pFrom = (LPCWSTR)&filechars;
    op.pTo = NULL;
    op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_NOERRORUI | FOF_SILENT;
    r = SHFileOperationW(&op);
    return Py_None;
}

static PyMethodDef TrashMethods[] = {
    {"send",  trash_win_send, METH_VARARGS, ""},
    {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
init_trash_win(void)
{
    PyObject *m = Py_InitModule("_trash_win", TrashMethods);
    if (m == NULL) {
        return;
    }
}