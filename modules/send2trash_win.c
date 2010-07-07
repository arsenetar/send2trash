/* Copyright 2010 Hardcoded Software (http://www.hardcoded.net)

This software is licensed under the "BSD" License as described in the "LICENSE" file, 
which should be included with this package. The terms are also available at 
http://www.hardcoded.net/licenses/bsd_license
*/

#define PY_SSIZE_T_CLEAN
#include "Python.h"

#define WINDOWS_LEAN_AND_MEAN
#include "windows.h"
#include "shlobj.h"

/* WARNING: If the filepath is not fully qualified, Windows deletes the file
   rather than sending it to trash. 
 */

static PyObject* send2trash_win_send(PyObject *self, PyObject *args)
{
    SHFILEOPSTRUCTW op;
    PyObject *filepath;
    Py_ssize_t len;
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
    memcpy(filechars, PyUnicode_AsUnicode(filepath), sizeof(WCHAR)*len);
    filechars[len] = '\0';
    filechars[len+1] = '\0';

    op.hwnd = 0;
    op.wFunc = FO_DELETE;
    op.pFrom = (LPCWSTR)&filechars;
    op.pTo = NULL;
    op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_NOERRORUI | FOF_SILENT;
    r = SHFileOperationW(&op);
    
    if (r != 0) {
        PyErr_Format(PyExc_OSError, "Couldn't perform operation. Error code: %d", r);
        return NULL;
    }
    
    return Py_None;
}

static PyMethodDef TrashMethods[] = {
    {"send",  send2trash_win_send, METH_VARARGS, ""},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef TrashDef = {
    PyModuleDef_HEAD_INIT,
    "send2trash_win",
    NULL,
    -1,
    TrashMethods,
    NULL,
    NULL,
    NULL,
    NULL
};

PyObject *
PyInit_send2trash_win(void)
{
    PyObject *m = PyModule_Create(&TrashDef);
    if (m == NULL) {
        return NULL;
    }
    return m;
}