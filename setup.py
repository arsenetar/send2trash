import sys
import os.path as op

from setuptools import setup
from distutils.extension import Extension

exts = []

if sys.platform == 'darwin':
    exts.append(Extension(
        '_send2trash_osx',
        [op.join('modules', 'send2trash_osx.c')],
        extra_link_args=['-framework', 'CoreServices'],
    ))
if sys.platform == 'win32':
    exts.append(Extension(
        '_send2trash_win',
        [op.join('modules', 'send2trash_win.c')],
        extra_link_args = ['shell32.lib'],
    ))

setup(
    name='Send2Trash',
    version='1.0.0',
    author='Hardcoded Software',
    author_email='hsoft@hardcoded.net',
    packages=['send2trash'],
    scripts=[],
    ext_modules = exts,
    url='http://www.hardcoded.net/docs/send2trash/',
    license='LICENSE',
    description='Send file to trash natively under Mac OS X, Windows and Linux.',
)