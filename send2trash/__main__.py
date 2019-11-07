# encoding: utf-8
from __future__ import print_function

import sys

from argparse import ArgumentParser
from send2trash import send2trash


def main(args=None):
    parser = ArgumentParser(description='Tool to send files to trash')
    parser.add_argument('files', nargs='+')
    parser.add_argument('-v', '--verbose', action='store_true', help='Print deleted files')
    args = parser.parse_args(args)

    for filename in args.files:
        try:
            send2trash(filename)
            if args.verbose:
                print('Trashed «' + filename + '»')
        except OSError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    main()
