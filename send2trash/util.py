# encoding: utf-8
# Copyright 2017 Virgil Dupras

# This software is licensed under the "BSD" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.hardcoded.net/licenses/bsd_license

import collections.abc


def preprocess_paths(paths):
    if isinstance(paths, collections.abc.Iterable) and not isinstance(paths, (str, bytes)):
        paths = list(paths)
    elif not isinstance(paths, list):
        paths = [paths]
    # Convert items such as pathlib paths to strings
    paths = [path.__fspath__() if hasattr(path, "__fspath__") else path for path in paths]
    return paths
