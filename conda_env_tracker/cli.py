#!/usr/bin/env python

# conda execute
# env:
#  - gitpython
#  - conda-execute
#  - yaml
# channels:
#  - minadyn
#  - conda-forge

from __future__ import print_function

import datetime
import contextlib
import logging
import os
import shutil
import tempfile

import conda.resolve
import conda.api
import conda_execute.config
from git import Repo
import yaml


def env_check(repo_dir):
    fname = os.path.join(repo_dir, 'env.spec')
    if not os.path.exists(fname):
        raise IOError("File {} doesn't exist.".format(fname))
    with open(fname) as fh:
        spec = yaml.safe_load(fh)
    env_spec = spec.get('env', [])
    index = conda.api.get_index(spec.get('channels', []))
    r = conda.resolve.Resolve(index)
    full_list_of_packages = sorted(r.solve(env_spec))
    return index, spec, full_list_of_packages


def build_manifest_branches(repo_directory):
    r = Repo(repo_directory)

    for remote in r.remotes:
        remote.fetch()

    for env in r.branches:
        name = env.name
        if 'manifest/' in name:
            continue
        env.checkout()
        spec_fname = os.path.join(repo_directory, 'env.spec')
        if not os.path.exists(spec_fname):
            # Skip branches which don't have a spec.
            continue
        index, spec, pkgs = env_check(repo_directory)
        manifest_branch_name = 'manifest/{}'.format(name)
        if manifest_branch_name in r.branches:
            manifest_branch = r.branches[manifest_branch_name]
        else:
            manifest_branch = r.create_head(manifest_branch_name)
        manifest_branch.checkout()
        manifest_path = os.path.join(repo_directory, 'env.manifest')
        with open(manifest_path, 'w') as fh:
            fh.write('\n'.join(pkgs))
        r.index.add([manifest_path])
        if r.is_dirty():
            r.index.commit('Manifest update from {:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now()))


@contextlib.contextmanager
def tempdir(prefix='tmp'):
    """A context manager for creating and then deleting a temporary directory."""
    tmpdir = tempfile.mkdtemp(prefix=prefix)
    try:
        yield tmpdir
    finally:
        if os.path.isdir(tmpdir):
            shutil.rmtree(tmpdir)


def main():
    import argparse
    import tempfile

    parser = argparse.ArgumentParser(description='Track environment specifications using a git repo.')
    parser.add_argument('repo_uri', help='Repo to use for environment tracking.')
    parser.add_argument('--verbose', '-v', action='store_true')
    args = parser.parse_args()

    log_level = logging.WARN
    if args.verbose:
        log_level = logging.DEBUG
    conda_execute.config.setup_logging(log_level)

    with tempdir() as repo_directory:
        repo = Repo.clone_from(args.repo_uri, repo_directory)
        for ref in repo.remotes.origin.refs:
            # Checkout each of the remote's branches, unless it has already been checked out
            # or is just HEAD. remote_head is just the name of the branch on the remote
            # (e.g. if the ref is origin/master, remote_head is just master).
            if ref.remote_head not in ['HEAD'] + [branch.name for branch in repo.branches]:
                # Create the branch from the remote branch.
                repo.create_head(ref.remote_head, ref).set_tracking_branch(ref)
        build_manifest_branches(repo_directory)
        for branch in repo.branches:
            if branch.name.startswith('manifest/'):
                remote_branch = branch.tracking_branch()
                if remote_branch is None or branch.commit != remote_branch.commit:
                    print('Pushing changes to {}'.format(branch.name))
                    repo.remotes.origin.push(branch)


if __name__ == '__main__':
    main()
