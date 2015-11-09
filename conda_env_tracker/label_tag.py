#!/usr/bin/env python
from __future__ import print_function

import datetime
from itertools import izip_longest
import os
import shutil
import time

from git import Repo
from conda_env_tracker.cli import tempdir, create_tracking_branches


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Update the next, current and previous labels of the given managed environment.')
    parser.add_argument('repo_uri', help='The repo to push the labels to.')
    parser.add_argument('next_tag', help='The tag to use for "next". The environment is deduced from that in the tag name.')
    parser.add_argument('--next-only', help='Whether to only update "next" and not current & previous.', action='store_true')
    args = parser.parse_args()

    with tempdir() as repo_directory:
        repo = Repo.clone_from(args.repo_uri, repo_directory)
        create_tracking_branches(repo)
        # Pull out the environment name from the form "env_<env_name>_2000_12_25".
        environment_name = args.next_tag.rsplit('_', 3)[0].split('_', 1)[1]
        env_branch = repo.branches[environment_name]
        env_branch.checkout()
        
        if not args.next_tag in repo.tags:
            raise RuntimeError('No tag {!r} exists in the repo.'.format(args.next_tag))

        labels_dir = os.path.join(repo.working_dir, 'labels')
        if not os.path.exists(labels_dir):
            os.makedirs(labels_dir)

        if args.next_only:
            label_progression = []
        else:
            label_progression = [('previous', None), ('current', 'previous'), ('next', 'current')]

        lbl_fname = lambda label: os.path.join(labels_dir, '{}.txt'.format(label))

        for label, next_label in label_progression:
            if os.path.exists(lbl_fname(label)):
                if next_label is None:
                    os.unlink(lbl_fname(label))
                else:
                    shutil.move(lbl_fname(label), lbl_fname(next_label))
                    repo.index.add([lbl_fname(next_label)])

        with open(lbl_fname('next'), 'w') as fh:
            fh.write(args.next_tag)

        repo.index.add([lbl_fname('next')])
        commit = repo.index.commit('Updated {} label to {}.'.format('next', args.next_tag))
        repo.remotes.origin.push(env_branch)


if __name__ == '__main__':
    main()
