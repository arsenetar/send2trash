Changes
=======

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
