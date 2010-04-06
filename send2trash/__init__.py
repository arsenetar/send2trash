import sys

if sys.platform == 'darwin':
    from plat_osx import send2trash
elif sys.platform == 'win32':
    from plat_win import send2trash
else:
    print "Unsupported platform"
