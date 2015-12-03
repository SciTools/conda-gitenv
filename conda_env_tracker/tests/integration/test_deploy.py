import contextlib
import os
import textwrap
import unittest

from git import Repo
from conda_env_tracker import resolve, tag_dates, label_tag, deploy
from setup_samples import create_repo, add_env, update_env


class Test(unittest.TestCase):
    def setUp(self):
        # Creates a new repo which is updated by conda-env-tracker
        repo = create_repo('deployable_2_envs')
        default = add_env(repo, 'default', """
            env:
             - python
            channels:
             - defaults 
            """)
        resolve.build_manifest_branches(repo)

        bleeding = add_env(repo, 'bleeding', """
            env:
             - python >2
             - numpy
            channels:
             - defaults 
            """)
        resolve.build_manifest_branches(repo)
        for tag in tag_dates.tag_by_branch(repo):
            label_tag.progress_label(repo, tag.name)

        update_env(repo, default, """
            env:
             - python 2.*
            channels: 
             - defaults 
            """)
        resolve.build_manifest_branches(repo)
        for tag in tag_dates.tag_by_branch(repo):
            self.default_next_tag = tag.name
            label_tag.progress_label(repo, tag.name)

        self.repo = repo

    def test(self):
        with resolve.tempdir() as tmpdir:
            deploy.deploy_repo(self.repo, tmpdir)

            def link_target(env, label):
                link = os.path.join(tmpdir, env, label)
                target = os.path.join(tmpdir, env, os.readlink(link))
                return target 

            self.assertTrue(os.path.exists(link_target('default', 'next')))
            self.assertTrue(os.path.exists(link_target('default', 'current')))
            self.assertTrue(os.path.exists(link_target('bleeding', 'next')))
            self.assertTrue(os.path.exists(link_target('bleeding', 'latest')))
            self.assertTrue(os.path.exists(link_target('default', 'latest')))

            # Check that we can resolve those links, finding the python executable.
            self.assertTrue(os.path.exists(os.path.join(tmpdir, 'bleeding', 'next', 'bin', 'python')))


if __name__ == '__main__':
    unittest.main()
