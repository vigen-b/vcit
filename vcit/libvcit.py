import argparse
import collections
import configparser
import hashlib
from math import ceil
import os
import re
import sys
import zlib


argparser = argparse.ArgumentParser(description='vcit - a simple version control system')
argsubparsers = argparser.add_subparsers(title='Command', dest='command', help='command to run', required=True)


def cmd_add(args):
    pass


def cmd_cat_file(args):
    pass


def cmd_checkout(args):
    pass


def cmd_commit(args):
    pass


def cmd_hash_object(args):
    pass


def cmd_init(args):
    pass


def cmd_log(args):
    pass


def cmd_ls_files(args):
    pass


def cmd_ls_tree(args):
    pass


def cmd_merge(args):
    pass


def cmd_rebase(args):
    pass


def cmd_rev_parse(args):
    pass


def cmd_rm(args):
    pass


def cmd_show_ref(args):
    pass


def cmd_tag(args):
    pass


def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)

    if   args.command == 'add'          : cmd_add(args)
    elif args.command == 'cat-file'     : cmd_cat_file(args)
    elif args.command == 'checkout'     : cmd_checkout(args)
    elif args.command == 'commit'       : cmd_commit(args)
    elif args.command == 'hash-object'  : cmd_hash_object(args)
    elif args.command == 'init'         : cmd_init(args)
    elif args.command == 'log'          : cmd_log(args)
    elif args.command == 'ls-files'     : cmd_ls_files(args)
    elif args.command == 'ls-tree'      : cmd_ls_tree(args)
    elif args.command == 'merge'        : cmd_merge(args)
    elif args.command == 'rebase'       : cmd_rebase(args)
    elif args.command == 'rev-parse'    : cmd_rev_parse(args)
    elif args.command == 'rm'           : cmd_rm(args)
    elif args.command == 'show-ref'     : cmd_show_ref(args)
    elif args.command == 'tag'          : cmd_tag(args)
