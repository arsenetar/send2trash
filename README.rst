==================================================
Send2Trash -- Send files to trash on all platforms
==================================================

Send2Trash is a small package that sends files to the Trash (or Recycle Bin) *natively* and on
*all platforms*. On OS X, it uses native ``FSMoveObjectToTrashSync`` Cocoa calls, on Windows, it
uses native (and ugly) ``SHFileOperation`` win32 calls. On other platforms, if `PyGObject`_ and
`GIO`_ are available, it will use this.  Otherwise, it will fallback to its own implementation
of the `trash specifications from freedesktop.org`_.

``ctypes`` is used to access native libraries, so no compilation is necessary.

Send2Trash supports Python 2.7 and up (Python 3 is supported).

Installation
------------

You can download it with pip::

    pip install Send2Trash

or you can download the source from http://github.com/hsoft/send2trash and install it with::

    >>> python setup.py install

Usage
-----

>>> from send2trash import send2trash
>>> send2trash('some_file')

On Freedesktop platforms (Linux, BSD, etc.), you may not be able to efficiently
trash some files. In these cases, an exception ``send2trash.TrashPermissionError``
is raised, so that the application can handle this case. This inherits from
``PermissionError`` (``OSError`` on Python 2). Specifically, this affects
files on a different device to the user's home directory, where the root of the
device does not have a ``.Trash`` directory, and we don't have permission to
create a ``.Trash-$UID`` directory.

For any other problem, ``OSError`` is raised.

.. _PyGObject: https://wiki.gnome.org/PyGObject
.. _GIO: https://developer.gnome.org/gio/
.. _trash specifications from freedesktop.org: http://freedesktop.org/wiki/Specifications/trash-spec/
