#!/usr/bin/env python
from __future__ import print_function

import datetime
import time

from git import Repo
from conda_env_tracker.cli import tempdir, create_tracking_branches


manifest_branch_prefix = 'manifest/'


def tag_by_branch(repo):
    # Iterate through each of the branches, and tag any changes with
    # the branch's commit timestamp.
    repo_tags_by_commit = {tag.commit: tag for tag in repo.tags}
    for branch in repo.branches:
        if branch.name.startswith(manifest_branch_prefix):
            sha = branch.commit
            env_name = branch.name[len(manifest_branch_prefix):]
            commit_date = datetime.datetime(*time.gmtime(sha.committed_date)[:6])
            if sha not in repo_tags_by_commit:
                tag_prefix = 'env-{}-{:%Y_%m_%d}'.format(env_name, commit_date)
                count, proposed_tag = 0, tag_prefix
                while proposed_tag in repo.tags:
                    count += 1
                    proposed_tag = '{}-{}'.format(tag_prefix, count)
                tag = repo.create_tag(proposed_tag, ref=branch,
                                      message="Automatic tag of {}.".format(env_name))
                yield tag


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Tag manifested environments based on the commit timestamp.')
    parser.add_argument('repo_uri', help='Repo to push tags to.')
    args = parser.parse_args()

    with tempdir() as repo_directory:
        repo = Repo.clone_from(args.repo_uri, repo_directory)
        create_tracking_branches(repo)
        for tag in tag_by_branch(repo):
            print('Pushing tag {}'.format(tag.name))
            repo.remotes.origin.push(tag)


if __name__ == '__main__':
    main()
