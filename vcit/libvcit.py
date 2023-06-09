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

# init
argsp = argsubparsers.add_parser('init', help='Initialize a new, empty repository.')
argsp.add_argument('path', metavar='directory', nargs='?', default='.', help='Where to create the repository.')

# cat-file
argsp = argsubparsers.add_parser('cat-file', help='Provide content of repository objects')
argsp.add_argument('type', metavar='type', choices=['blob', 'commit', 'tag', 'tree'], help='Specify the type')
argsp.add_argument('object', metavar='object', help='The object to display')

# hash-object
argsp = argsubparsers.add_parser('hash-object', help='Compute object ID and optionally creates a blob from a file')
argsp.add_argument('-t', metavar='type', dest='type', choices=['blob', 'commit', 'tag', 'tree'], default='blob', help='Specify the type')
argsp.add_argument('-w', dest='write', action='store_true', help='Actually write the object into the database')
argsp.add_argument('path', help='Read object from <file>')


class GitRepository:
    """A Git repository"""

    worktree = None
    gitdir = None
    conf = None

    def __init__(self, path, force=False):
        self.worktree = path
        self.gitdir = os.path.join(path, '.git')

        if not (force or os.path.isdir(self.gitdir)):
            raise Exception('Not a Git repository %s' % path)

        # Read configuration file
        self.conf = configparser.ConfigParser()
        cf = repo_file(self, 'config')

        if cf and os.path.exists(cf):
            self.conf.read([cf])
        elif not force:
            raise Exception('Configuration file missing')

        if not force:
            vers = int(self.conf.get('core', 'repositoryformatversion'))
            if vers != 0:
                raise Exception('Unsupported repositoryformatversion %s' % vers)


def repo_path(repo, *path):
    """Compute path under repo's gitdir"""
    return os.path.join(repo.gitdir, *path)


def repo_file(repo, *path, mkdir=False):
    """Same as repo_path, but create dirname(*path) if absent. For
    example, repo_file(r, \"refs\", \"remotes\", \"origin\", \"HEAD\") will create
    .git/refs/remotes/origin."""

    if repo_dir(repo, *path[:-1], mkdir=mkdir):
        return repo_path(repo, *path)


def repo_dir(repo, *path, mkdir=False):
    """Same as repo path, but mkdir *path if absent if mkdir."""

    path = repo_path(repo, *path)

    if os.path.exists(path):
        if os.path.isdir(path):
            return path
        else:
            raise Exception('Not a directory %s', path)

    if mkdir:
        os.makedirs(path)
        return path
    else:
        return None


def repo_create(path):
    """Create a new repository at path."""

    repo = GitRepository(path, True)

    if os.path.exists(repo.worktree):
        if not os.path.isdir(repo.worktree):
            raise Exception('%s is not a directory', repo.worktree)
        if os.listdir(repo.worktree):
            raise Exception('%s is not empty!', repo.worktree)
    else:
        os.makedirs(repo.worktree)

    assert(repo_dir(repo, 'branches', mkdir=True))
    assert(repo_dir(repo, 'objects', mkdir=True))
    assert(repo_dir(repo, 'refs', 'tags', mkdir=True))
    assert(repo_dir(repo, 'refs', 'heads', mkdir=True))

    # .git/description
    with open(repo_file(repo, 'description'), 'w') as f:
        f.write('Unnamed repository; edit this file \'description\' to name the repository.\n')

    # .git/HEAD
    with open(repo_file(repo, 'HEAD'), 'w') as f:
        f.write('ref: refs/heads/master\n')

    with open(repo_file(repo, 'config'), 'w') as f:
        config = repo_default_config()
        config.write(f)

    return repo


def repo_find(path='.', required=True):
    path = os.path.realpath(path)

    if os.path.realpath(os.path.join(path, '.git')):
        return GitRepository(path)

    parent = os.path.realpath(os.path.join(path, '..'))

    if parent == path:
        # Bottom case
        # os.path.join('/', '..') == '/'.
        # If parent==path, then path is root.

        if required:
            raise Exception('No git repository.')
        else:
            return None

    # recursion
    return repo_find(parent, required)


def repo_default_config():
    ret = configparser.ConfigParser()

    ret.add_section('core')
    ret.set('core', 'repositoryformatversion', '0')
    ret.set('core', 'filemode', 'false')
    ret.set('core', 'bare', 'false')

    return ret


class GitObject:
    """Abstracts git object

    Git object has predefined structure: It starts with object type followed by
    then ASCII space (0x20), then length of the file and null separator (0x00).
    Then followed content of the file
    """

    repo = None

    def __init__(self, repo, data=None):
        self.repo = repo

        if data is not None:
            self.deserialize(data)

    def serialize(self):
        """Converts content to readable format"""
        raise Exception('Unimplemented!')

    def deserialize(self, data):
        raise Exception('Unimplemented!')


class GitCommit(GitObject):
    fmt = b'commit'

    def deserialize(self, data):
        self.kvlm = kvlm_parse(data)

    def serialize(self):
        return kvlm_serialize(self.kvlm)


class GitTree(GitObject):
    pass


class GitTag(GitObject):
    pass


class GitBlob(GitObject):
    fmt = b'blob'

    def serialize(self):
        return self.blobdata

    def deserialize(self, data):
        self.blobdata = data


def object_find(repo, name, fmt=None, follow=True):
    return name


def object_read(repo, sha):
    """Read object object_id from Git repository repo. Return a GitObject whose
    exact type depends on the object."""

    path = repo_path(repo, 'objects', sha[0:2], sha[2:])

    with open(path, 'rb') as f:
        raw = zlib.decompress(f.read())

        # Read object type
        x = raw.find(b' ')
        fmt = raw[0:x]

        # Read and validate object size
        y = raw.find(b'\x00', x)
        size = int(raw[x:y].decode('ascii'))
        if size != len(raw)-y-1:
            raise Exception('Malformed object {0}: bad length'.format(sha))

        # Pick constructor
        if fmt == b'commit' : c=GitCommit
        elif fmt == b'tree' : c=GitTree
        elif fmt == b'tag'  : c=GitTag
        elif fmt == b'blob' : c=GitBlob
        else:
            raise Exception('Unknown type %s for object %s'.format(fmt.decode('ascii'), sha))

        # Call constructor and return object
        return c(repo, raw[y+1:])


def object_write(obj, actually_write=True):
    """Write object to the Git repository repo. Return the object's sha."""

    # Serialize object data
    data = obj.serialize()

    # Add header
    result = obj.fmt + b' ' + str(len(data)).encode() + b'\x00' + data

    # Compute hash
    sha = hashlib.sha1(result).hexdigest()

    if actually_write:
        # Compute path
        path = repo_file(obj.repo, 'objects', sha[0:2], sha[2:], mkdir=actually_write)

        # Write to file
        with open(path, 'wb') as f:
            f.write(zlib.compress(result))

    return sha


def cat_file(repo, obj, fmt=None):
    obj = object_find(repo, obj, fmt=fmt, follow=True)
    obj = object_read(repo, obj)
    sys.stdout.buffer.write(obj.serialize())


def object_hash(fd, fmt, repo=None):
    data = fd.read()

    if fmt == b'commit':
        obj = GitCommit(repo, data)
    elif fmt == b'tree':
        obj = GitTree(repo, data)
    elif fmt == b'tag':
        obj = GitTag(repo, data)
    elif fmt == b'blob':
        obj = GitBlob(repo, data)
    else:
        raise Exception('Unknown type %s!' % fmt.decode('ascii'))

    return object_write(obj, repo)


def kvlm_parse(raw, start=0, dct=None):
    """key-value list and message parser"""
    if not dct:
        dct = collections.OrderedDict()

    # search next space and new line
    spc = raw.find(b' ', start)
    nl = raw.find(b'\n', start)

    # if newline is the first or there is no space, then
    # remains message
    if (spc < 0) or (nl < spc):
        assert(nl == start)
        dct[b''] = raw[start+1:]
        return dct

    # parse key values recursive
    key = raw[start:spc]

    end = start
    while True:
        end = raw.find(b'\n', end+1)
        if raw[end+1] != ord(' '):
            break

    # grab the value and remove leading spaces
    value = raw[spc+1, end].replace(b'\n ', b' ')

    # don't override existing value
    if key in dict:
        if type(dct[key]) == list:
            dct[key].append(value)
        else:
            dct[key] = [dct[key], value]
    else:
        dct[key] = value

    return kvlm_parse(raw, start=end+1, dct=dct)


def kvlm_serialize(kvlm):
    """key-value list and message serializer"""
    ret = b''

    # output fields
    for k in kvlm.keys():
        # skip the message itself
        if k == b'':
            continue

        val = kvlm[k]
        # normalize to list
        if type(val) != list:
            val = [val]

        for v in val:
            ret += k + b' ' + (v.replace(b'\n', b'\n ')) + b'\n'

    # append message
    ret += b'\n' + kvlm[b'']

    return ret


def cmd_add(args):
    pass


def cmd_cat_file(args):
    repo = repo_find()
    cat_file(repo, args.object, fmt=args.type.encode())


def cmd_checkout(args):
    pass


def cmd_commit(args):
    pass


def cmd_hash_object(args):
    if args.write:
        repo = GitRepository('.')
    else:
        repo = None

    with open(args.path, 'rb') as fd:
        sha = object_hash(fd, args.type.encode(), repo=repo)
        print(sha)


def cmd_init(args):
    repo_create(args.path)


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
