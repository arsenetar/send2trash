import sys
import unittest


def TestSuite():
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    if sys.platform == "win32":
        from . import test_plat_win

        suite.addTests(loader.loadTestsFromModule(test_plat_win))
    else:
        from . import test_script_main
        from . import test_plat_other

        suite.addTests(loader.loadTestsFromModule(test_script_main))
        suite.addTests(loader.loadTestsFromModule(test_plat_other))
    return suite
