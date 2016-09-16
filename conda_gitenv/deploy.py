#!/usr/bin/env python
from __future__ import print_function

import datetime
from glob import glob
import os
import time

from git import Repo
import conda.api
import conda.fetch
from conda_gitenv.resolve import tempdir, create_tracking_branches

from conda_gitenv.lock import Locked
from conda_gitenv import manifest_branch_prefix


def tags_by_label(labels_directory):
    tags = {}
    if os.path.isdir(labels_directory):
        for label_fname in glob(os.path.join(labels_directory, '*.txt')):
            with open(label_fname, 'r') as fh:
                tag_name = fh.read().strip()
            label = os.path.splitext(os.path.basename(label_fname))[0]
            tags[label] = tag_name
    return tags


def tags_by_env(repo):
    tags = {}
    for tag in repo.tags:
        env_name = tag.name.split('-')[1]
        tags.setdefault(env_name, []).append(tag)
    return tags


def deploy_tag(repo, tag_name, target):
    tag = repo.tags[tag_name]
    # Checkout the tag in a detached head form.
    repo.head.reference = tag.commit
    repo.head.reset(working_tree=True)

    # Pull out the environment name from the form "env-<env_name>-<deployed_name>".
    env_name = tag_name.split('-')[1]
    deployed_name = tag_name.split('-', 2)[2]

    manifest_fname = os.path.join(repo.working_dir, 'env.manifest')
    if not os.path.exists(manifest_fname):
        raise ValueError("The tag '{}' doesn't have a manifested environment.".format(tag_name))
    with open(manifest_fname, 'r') as fh:
        manifest = sorted(line.strip().split('\t') for line in fh)
    create_env(manifest, os.path.join(target, env_name, deployed_name), os.path.join(target, '.pkg_cache'))


def create_env(pkgs, target, pkg_cache):
    # We lock the specific environment we are wanting to create. If other requests come in for the
    # exact same environment, they will have to wait for this to finish (good).
    with Locked(target):
        pkg_names = set(pkg for _, pkg in pkgs)
        if os.path.exists(target):
            # The environment we want to deploy already exists. We should just double check that
            # there aren't already packages in there which we need to remove before we install anything
            # new.
            linked = conda.install.linked(target)
            for pkg in linked:
                if pkg not in pkg_names:
                    conda.install.unlink(target, pkg)
        else:
            linked = []

        if set(linked) == pkg_names:
            # We don't need to re-link everything - it is already as expected.
            # The downside is that we are not verifying that each package is installed correctly.
            return

        for source, pkg in pkgs:
            index = conda.fetch.fetch_index([source], use_cache=False)
            # Deal with the fact that a recent conda includes the source in the index key.
            index = {pkg['fn']: pkg for pkg in index.values()}

            tar_name = pkg + '.tar.bz2'
            pkg_info = index.get(tar_name, None)
            if pkg_info is None:
                raise ValueError('Distribution {} is no longer available in the channel.'.format(tar_name))
            dist_name = pkg 
            # We force a lock on retrieving anything which needs access to a distribution of this
            # name. If other requests come in to get the exact same package they will have to wait
            # for this to finish (good). If conda itself it fetching these pacakges then there is
            # the potential for a race condition (bad) - there is no solution to this unless
            # conda/conda is updated to be more precise with its locks.
            lock_name = os.path.join(pkg_cache, dist_name)
            with Locked(lock_name):
                schannel_dist_name='{}::{}'.format(pkg_info['schannel'], dist_name)
                if not conda.install.is_extracted(schannel_dist_name):
                    if not conda.install.is_fetched(schannel_dist_name):
                        print('Fetching {}'.format(dist_name))
                        conda.fetch.fetch_pkg(pkg_info)
                    conda.install.extract(schannel_dist_name)
                conda.install.link(target, schannel_dist_name)


def deploy_repo(repo, target):
    env_tags = tags_by_env(repo)
    for branch in repo.branches:
        # We only want environment branches, not manifest branches.
        if not branch.name.startswith(manifest_branch_prefix):
            manifest_branch_name = manifest_branch_prefix + branch.name
            # If there is no equivalent manifest branch, we need to
            # skip this environment.
            if manifest_branch_name not in repo.branches:
                continue
            manifest_branch = repo.branches[manifest_branch_name]
            branch.checkout()
            labelled_tags = tags_by_label(os.path.join(repo.working_dir, 'labels'))
            # We want to deploy all tags which have a label, as well as the latest tag.
            if env_tags.get(branch.name):
                latest_tag = max(env_tags[branch.name],
                                 key=lambda t: t.commit.committed_date)
                labelled_tags['latest'] = latest_tag.name
            for tag in set(labelled_tags.values()):
                deploy_tag(repo, tag, target)
            for label, tag in labelled_tags.items():
                with Locked(os.path.join(target, label)):
                    deployed_name = tag.split('-', 2)[2]
                    label_target = deployed_name
                    label_location = os.path.join(target, branch.name, label)

                    if os.path.exists(label_location):
                        # Unix only:
                        if os.readlink(label_location) != label_target:
                            os.remove(label_location)
                   
                    if not os.path.exists(label_location):
                        print('Linking {}/{} to {}'.format(branch.name, label, tag))
                        os.symlink(label_target, label_location)

def configure_parser(parser):
    parser.add_argument('repo_uri', help='Repo to deploy.')
    parser.add_argument('target', help='Location to deploy the environments to.')
    parser.set_defaults(function=handle_args)
    return parser


def handle_args(args):
    with tempdir() as repo_directory:
        repo = Repo.clone_from(args.repo_uri, repo_directory)
        create_tracking_branches(repo)
        deploy_repo(repo, args.target)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Deploy the tracked environments.')
    configure_parser(parser)
    args = parser.parse_args()
    return args.function(args)


if __name__ == '__main__':
    main()
