Changes
=======

Version 1.8.2 -- 2023/04/27
---------------------------
* win/legacy: tiny logic simplification by @BoboTiG in https://github.com/arsenetar/send2trash/pull/77
* TravisCI is not used anymore by @sobolevn in https://github.com/arsenetar/send2trash/pull/73
* fix(ci): Update to latest actions, fix python versions by @arsenetar in https://github.com/arsenetar/send2trash/pull/78

Version 1.8.1b0 -- 2021/09/20
-----------------------------
* Add fallback to HOMETRASH when cross device errors happen in plat_other (#26, #41, #63)

Version 1.8.0 -- 2021/08/08
---------------------------

* Add compatibility with pathlib paths (#49)
* Fix thread compatibility of modern windows implementation (#59)
* Fix handling of UNC names in legacy windows implementation  (#57)

Version 1.7.1 -- 2021/06/21
---------------------------

* Release stable version with changes from last 3 releases
* Fix handling of UNC names (#57)

Version 1.7.0a1 -- 2021/05/14
-----------------------------

* Changed conditional for when to try to use pyobjc version (#51)

Version 1.7.0a0 -- 2021/04/20
-----------------------------

* Add console_script entry point (#50)
* Increased python CI versions (#52, #54)
* Fix minor issue in setup.py (#53)
* Fix issue with windows tests importing modules on non-windows (#55)
* Unit test cleanups, rewrites, and flake8 cleanups
* Windows: Fix legacy windows platform for multi-byte unicode and add tests
* macOS: Add alternative pyobjc version to potentially improve compatibility (#51)

Version 1.6.0b1 -- 2020/06/18
-----------------------------

* Add main method which allows calling via ``python -m send2trash somefile``
* Windows: Add support for using IFileOperation when pywin32 is present on Vista and newer
* Add support for passing multiple files at once in a list
* Windows: Batch multi-file calls to improve performance (#42)
* Windows: Fix issue with SHFileOperation failing silently when path is not found (#33)

Version 1.5.0 -- 2018/02/16
---------------------------

* More specific error when failing to create XDG fallback trash directory (#20)
* Windows: Workaround for long paths (#23)

Version 1.4.2 -- 2017/11/17
---------------------------

* Fix incompatibility with Python 3.6 on Windows. (#18)

Version 1.4.1 -- 2017/08/07
---------------------------

* Fix crash on Windows introduced in v1.4.0. Oops... (#14)

Version 1.4.0 -- 2017/08/07
---------------------------

* Use ``bytes`` instead of ``str`` for internal path handling in ``plat_other``. (#13)

Version 1.3.1 -- 2017/07/31
---------------------------

* Throw ``WindowsError`` instead of ``OSError`` in ``plat_win``. (#7)
* Fix ``TypeError`` on python 2 in ``plat_other``. (#12)

Version 1.3.0 -- 2013/07/19
---------------------------

* Added support for Gnome's GIO.
* Merged Python 3 and Python 2 versions in a single codebase.

Version 1.2.0 -- 2011/03/16
---------------------------

* Improved ``plat_other`` to follow freedesktop.org trash specification.

Version 1.1.0 -- 2010/10/18
---------------------------

* Converted compiled modules to ctypes so that cross-platform compilation isn't necessary anymore.

Version 1.0.2 -- 2010/07/10
---------------------------

* Fixed bugs with external volumes in plat_other.

Version 1.0.1 -- 2010/04/19
---------------------------

* Fixed memory leak in OS X module.

Version 1.0.0 -- 2010/04/07
---------------------------

* Initial Release
