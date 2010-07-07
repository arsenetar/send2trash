import sys
import os.path as op

from setuptools import setup
from distutils.extension import Extension

exts = []

if sys.platform == 'darwin':
    exts.append(Extension(
        'send2trash_osx',
        [op.join('modules', 'send2trash_osx.c')],
        extra_link_args=['-framework', 'CoreServices'],
    ))
if sys.platform == 'win32':
    exts.append(Extension(
        'send2trash_win',
        [op.join('modules', 'send2trash_win.c')],
        extra_link_args = ['shell32.lib'],
    ))

CLASSIFIERS = [
    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: BSD License',
    'Operating System :: MacOS :: MacOS X',
    'Operating System :: Microsoft :: Windows',
    'Operating System :: POSIX',
    'Programming Language :: Python :: 3',
    'Programming Language :: Objective C',
    'Programming Language :: C',
    'Topic :: Desktop Environment :: File Managers',
]

setup(
    name='Send2Trash3k',
    version='1.0.1',
    author='Hardcoded Software',
    author_email='hsoft@hardcoded.net',
    packages=['send2trash'],
    scripts=[],
    ext_modules = exts,
    url='http://hg.hardcoded.net/send2trash/',
    license='BSD License',
    description='Send file to trash natively under Mac OS X, Windows and Linux.',
    long_description=open('README').read(),
    classifiers=CLASSIFIERS,
    zip_safe=False,
)