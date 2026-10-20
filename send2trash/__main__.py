# Copyright 2017 Virgil Dupras

# This software is licensed under the "BSD" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.hardcoded.net/licenses/bsd_license

import sys

from argparse import ArgumentParser
from send2trash import send2trash

if sys.version_info[0] < 3:
    raise RuntimeError("send2trash is only compatible with Python 3 and above (use versions <= 1.8.3 for python 2).")


def main(args=None):
    parser = ArgumentParser(description="Tool to send files to trash")
    parser.add_argument("files", nargs="+")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print deleted files")
    parser.add_argument(
        "--continue-on-error", action="store_true", help="Continue with remaining files after an error (exit status is still 1)"
    )
    args = parser.parse_args(args)

    failed = False
    for filename in args.files:
        try:
            send2trash(filename)
            if args.verbose:
                print("Trashed «" + filename + "»")
        except OSError as e:
            print(str(e), file=sys.stderr)
            if not args.continue_on_error:
                sys.exit(1)
            failed = True

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
