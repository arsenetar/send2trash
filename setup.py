from setuptools import setup

CLASSIFIERS = [
    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: BSD License',
    'Operating System :: MacOS :: MacOS X',
    'Operating System :: Microsoft :: Windows',
    'Operating System :: POSIX',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Topic :: Desktop Environment :: File Managers',
]

LONG_DESCRIPTION = open('README.rst', 'rt').read() + '\n\n' + open('CHANGES.rst', 'rt').read()

setup(
    name='Send2Trash',
    version='1.4.0',
    author='Virgil Dupras',
    author_email='hsoft@hardcoded.net',
    packages=['send2trash'],
    scripts=[],
    test_suite='tests',
    url='https://github.com/hsoft/send2trash',
    license='BSD License',
    description='Send file to trash natively under Mac OS X, Windows and Linux.',
    long_description=LONG_DESCRIPTION,
    classifiers=CLASSIFIERS,
)
