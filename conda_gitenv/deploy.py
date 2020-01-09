#!/usr/bin/env python
from __future__ import print_function

from fnmatch import fnmatch
from functools import wraps
from glob import glob
import os
import stat

import conda.base.context
from conda.core.link import UnlinkLinkTransaction
from conda.core.package_cache import ProgressiveFetchExtract
from conda.exports import Resolve, fetch_index
from conda.models.channel import prioritize_channels
from conda.models.dist import Dist
from conda.gateways.disk.create import mkdir_p
from git import Repo
import yaml

from conda_gitenv.lock import Locked
from conda_gitenv.resolve import create_tracking_branches, tempdir
from conda_gitenv import manifest_branch_prefix


PKG_CACHE_NAME = '.pkg_cache'


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


def deploy_tag(repo, tag_name, target, api_user=None, api_key=None,
               mirror=None):
    tag = repo.tags[tag_name]
    # Checkout the tag in a detached head form.
    repo.head.reference = tag.commit
    repo.head.reset(working_tree=True)

    # Parse tag_name with form "env-<env_name>-<deployed_name>".
    env_name = tag_name.split('-')[1]
    deployed_name = tag_name.split('-', 2)[2]

    manifest_fname = os.path.join(repo.working_dir, 'env.manifest')
    if not os.path.exists(manifest_fname):
        msg = "The tag '{}' doesn't have a manifested environment."
        raise ValueError(msg.format(tag_name))
    with open(manifest_fname, 'r') as fh:
        manifest = sorted(line.strip().split('\t') for line in fh)

    # Replace the channel URL with the mirror URL for each package
    # entry specified in the manifest.
    if mirror is not None:
        manifest = [[mirror, pkg] for channel, pkg in manifest]

    target = os.path.join(target, env_name, deployed_name)
    create_env(repo, manifest, target, api_user=api_user, api_key=api_key,
               mirror=mirror)


def create_env(repo, pkgs, target, api_user=None, api_key=None, mirror=None):
    try:
        # Python3...
        from urllib.parse import urlparse
    except ImportError:
        # Python2...
        from urlparse import urlparse

    with Locked(target):
        spec_fname = os.path.join(repo.working_dir, 'env.spec')
        with open(spec_fname, 'r') as fh:
            spec = yaml.safe_load(fh)

        channels = spec.get('channels', [])

        # Replace the channel/s specified in the environment specification
        # with the mirror URL.
        if mirror is not None:
            channels = [mirror]

        if api_user and api_key:
            # Inject the API user and key into the channel URLs...
            for i, url in enumerate(channels):
                parts = urlparse(url)
                api_url = '{}://{}:{}@{}{}'.format(parts.scheme, api_user,
                                                   api_key, parts.netloc,
                                                   parts.path)
                channels[i] = api_url
            # Inject the API user and key into the manifest URLs...
            for i, (url, _) in enumerate(pkgs):
                parts = urlparse(url)
                api_url = '{}://{}:{}@{}{}'.format(parts.scheme, api_user,
                                                   api_key, parts.netloc,
                                                   parts.path)
                pkgs[i][0] = api_url

        channels = prioritize_channels(channels)
        # Build reverse look-up from channel URL to channel name.
        channel_by_url = {url: channel
                          for url, (channel, _) in channels.items()}
        index = fetch_index(channels, use_cache=False)
        resolver = Resolve(index)
        # Create the package distribution from the manifest. Ensure to replace
        # channel-URLs with channel names, otherwise the fetch-extract may fail
        dists = [Dist.from_string(pkg,
                                  channel_override=channel_by_url.get(url,
                                                                      url))
                 for url, pkg in pkgs]
        # Use the resolver to sort packages into the appropriate dependency
        # order.
        sorted_dists = resolver.dependency_sort({dist.name: dist
                                                 for dist in dists})

        pfe = ProgressiveFetchExtract(index, sorted_dists)
        pfe.execute()
        mkdir_p(target)
        txn = UnlinkLinkTransaction.create_from_dists(index, target, (),
                                                      sorted_dists)
        txn.execute()


def _patch_pkgs_dirs(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        orig_pkgs_dirs = conda.base.context.Context.pkgs_dirs

        if len(args) >= 2:
            # Sniff the args to get the target deployment directory.
            target = args[1]
            # The associated target deployment custom package cache directory.
            pkg_cache = os.path.join(target, PKG_CACHE_NAME)

            @property
            def mocker(self):
                return (pkg_cache,)

            # Monkey patch the context pkgs_dirs property to override
            # it with our custom package cache directory.
            conda.base.context.Context.pkgs_dirs = mocker

        result = func(*args, **kwargs)

        # Undo the monkey patch of the context pkgs_dirs property.
        conda.base.context.Context.pkgs_dirs = orig_pkgs_dirs

        return result

    return wrapper


@_patch_pkgs_dirs
def deploy_repo(repo, target, env_labels=None, api_user=None, api_key=None,
                mirror=None):
    env_tags = tags_by_env(repo)

    for branch in repo.branches:
        # We only want environment branches, not manifest branches.
        if not branch.name.startswith(manifest_branch_prefix):
            manifest_branch_name = manifest_branch_prefix + branch.name
            # If there is no equivalent manifest branch, we need to
            # skip this environment.
            if manifest_branch_name not in repo.branches:
                continue
            branch.checkout()
            all_labelled_tags = tags_by_label(os.path.join(repo.working_dir,
                                                           'labels'))

            # Create a latest tag that points to the most recently tagged
            # environment.
            if env_tags.get(branch.name):
                latest_tag = max(env_tags[branch.name],
                                 key=lambda t: t.commit.committed_date)
                all_labelled_tags['latest'] = latest_tag.name

            # Only deploy environments that match the given pattern.
            labelled_tags = {}
            if env_labels is None:
                env_labels = ['*']
            for label, tag in all_labelled_tags.items():
                item = '{}/{}'.format(branch.name, label)
                match = [fnmatch(item, env_label)
                         for env_label in env_labels]
                if any(match):
                    labelled_tags[label] = tag

            for tag in set(labelled_tags.values()):
                deploy_tag(repo, tag, target,
                           api_user=api_user, api_key=api_key, mirror=mirror)

            # Lock down the package cache files which may contain
            # API credentials.
            mode = stat.S_IRUSR | stat.S_IWUSR
            pkg_cache_urls = os.path.join(target, PKG_CACHE_NAME, 'urls.txt')
            if os.path.isfile(pkg_cache_urls):
                os.chmod(pkg_cache_urls, mode)

            pkg_cache_urls = os.path.splitext(pkg_cache_urls)[0]
            if os.path.isfile(pkg_cache_urls):
                os.chmod(pkg_cache_urls, mode)

            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR
            for label, tag in labelled_tags.items():
                with Locked(os.path.join(target, label)):
                    deployed_name = tag.split('-', 2)[2]
                    label_target = deployed_name
                    label_location = os.path.join(target, branch.name, label)

                    if os.path.exists(label_location):
                        if os.readlink(label_location) != label_target:
                            os.remove(label_location)
                   
                    if not os.path.exists(label_location):
                        msg = 'Linking {}/{} to {} ({})'
                        print(msg.format(branch.name, label,
                                         label_target, tag))
                        os.symlink(label_target, label_location)

                    # Lock down the conda-meta directory, which may contain
                    # API credentials.
                    conda_meta = os.path.join(target, branch.name,
                                              label_target, 'conda-meta')
                    if os.path.isdir(conda_meta):
                        os.chmod(conda_meta, mode)


def configure_parser(parser):
    parser.add_argument('repo_uri', help='Repo to deploy.')
    parser.add_argument('target', help='Location to deploy the environments.')
    parser.add_argument('--api_key', '-k', action='store',
                        help='the API key')
    parser.add_argument('--api_user', '-u', action='store',
                        help='the API user')
    parser.add_argument('--env_labels', nargs='+', default=['*'],
                        help='Pattern to match environment labels to. In the '
                             'form "{environment}/{label}".', )
    parser.add_argument('--mirror', '-m', action='store',
                        help='the replacement mirror channel URL')
    parser.set_defaults(function=handle_args)
    return parser


def handle_args(args):
    with tempdir() as repo_directory:
        repo = Repo.clone_from(args.repo_uri, repo_directory)
        create_tracking_branches(repo)
        deploy_repo(repo, args.target, env_labels=args.env_labels,
                    api_user=args.api_user, api_key=args.api_key,
                    mirror=args.mirror)


def main():
    import argparse

    description = 'Deploy the tracked environments.'
    parser = argparse.ArgumentParser(description=description)
    configure_parser(parser)
    args = parser.parse_args()
    return args.function(args)


if __name__ == '__main__':
    main()
