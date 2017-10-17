#!/usr/bin/env python
from __future__ import print_function

import datetime
import fnmatch
from glob import glob
import os
import time

from git import Repo
import yaml

from conda_gitenv.lock import Locked
from conda_gitenv.resolve import create_tracking_branches, tempdir
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


def deploy_tag(repo, tag_name, target, pkg_cache):
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

    target = os.path.join(target, env_name, deployed_name)
    create_env(repo, manifest, target, pkg_cache)


def create_env(repo, pkgs, target, pkg_cache):
    from conda.core.link import UnlinkLinkTransaction
    from conda.core.package_cache import ProgressiveFetchExtract
    from conda.exports import Resolve, fetch_index
    from conda.models.channel import prioritize_channels
    from conda.models.dist import Dist
    from conda.gateways.disk.create import mkdir_p

    spec_fname = os.path.join(repo.working_dir, 'env.spec')

    # Skip branches that don't have an environment specification
    if not os.path.exists(spec_fname):
        return

    with Locked(target):
        with open(spec_fname, 'r') as fh:
            spec = yaml.safe_load(fh)

        channels = prioritize_channels(spec.get('channels', []))
        # Build reverse look-up from channel URL to channel name.
        channel_by_url = {url: channel for url, (channel, _) in channels.items()}
        index = fetch_index(channels, use_cache=False)
        resolver = Resolve(index)
        # Create the package distribution from the manifest. Ensure to replace
        # channel-URLs with channel names, otherwise the fetch-extract may fail.
        dists = [Dist.from_string(pkg, channel_override=channel_by_url.get(url, url)) for url, pkg in pkgs]
        # Use the resolver to sort packages into the appropriate dependency
        # order.
        sorted_dists = resolver.dependency_sort({dist.name: dist for dist in dists})

        pfe = ProgressiveFetchExtract(index, dists)
        pfe.execute()
        mkdir_p(target)
        txn = UnlinkLinkTransaction.create_from_dists(index, target, (), dists)
        txn.execute()


def deploy_repo(repo, target, desired_env_labels=None):
    # Set pkgs_dirs location to be the specified pkg_cache.
    # Cache settings to be reinstated at the end.
    import conda.base.context

    pkg_cache = os.path.join(target, '.pkg_cache')
    @property
    def mocker(self):
        return (pkg_cache,)
    orig_pkgs_dirs = conda.base.context.Context.pkgs_dirs
    # Monkey patch the context pkgs_dirs property to override it
    # with our custom package cache directory.
    conda.base.context.Context.pkgs_dirs = mocker

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
            all_labelled_tags = tags_by_label(os.path.join(repo.working_dir, 'labels'))

            # Create a latest tag that points to the most recently tagged environment.
            if env_tags.get(branch.name):
                latest_tag = max(env_tags[branch.name],
                                 key=lambda t: t.commit.committed_date)
                all_labelled_tags['latest'] = latest_tag.name

            # Only deploy environments that match the given pattern.
            labelled_tags = {}
            if desired_env_labels is None:
                desired_env_labels = ['*']
            for label, tag in all_labelled_tags.items():
                if any([fnmatch.fnmatch('{}/{}'.format(branch.name, label),
                                        env_label) for env_label in desired_env_labels]):
                    labelled_tags[label] = tag

            for tag in set(labelled_tags.values()):
                deploy_tag(repo, tag, target, pkg_cache)

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

    # Undo the monkey patch of the context pkgs_dirs property.
    conda.base.context.Context.pkgs_dirs = orig_pkgs_dirs


def configure_parser(parser):
    parser.add_argument('repo_uri', help='Repo to deploy.')
    parser.add_argument('target', help='Location to deploy the environments to.')
    parser.add_argument('--env_labels', nargs='+',  default=['*'], 
                        help='Pattern to match environment labels to. In the '
                             'form "{environment}/{label}".',)
    parser.set_defaults(function=handle_args)
    return parser


def handle_args(args):
    with tempdir() as repo_directory:
        repo = Repo.clone_from(args.repo_uri, repo_directory)
        create_tracking_branches(repo)
        deploy_repo(repo, args.target, args.env_labels)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Deploy the tracked environments.')
    configure_parser(parser)
    args = parser.parse_args()
    return args.function(args)


if __name__ == '__main__':
    main()
