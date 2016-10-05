import contextlib
import os
import textwrap
import unittest

from git import Repo
from conda_gitenv import resolve, tag_dates, label_tag, deploy
from conda_gitenv.tests.integration.setup_samples import (create_repo, add_env,
                                                          update_env)


class Test(unittest.TestCase):
    def setUp(self):
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

    def check_link_exists(self, tmpdir, env, label):
        link = os.path.join(tmpdir, env, label)
        target = os.path.join(tmpdir, env, os.readlink(link))
        return os.path.exists(target)

    def test(self):
        with resolve.tempdir() as tmpdir:
            deploy.deploy_repo(self.repo, tmpdir)

            self.assertTrue(self.check_link_exists(tmpdir, 'default', 'next'))
            self.assertTrue(self.check_link_exists(tmpdir, 'default', 'current'))
            self.assertTrue(self.check_link_exists(tmpdir, 'bleeding', 'next'))
            self.assertTrue(self.check_link_exists(tmpdir, 'bleeding', 'latest'))
            self.assertTrue(self.check_link_exists(tmpdir, 'default', 'latest'))

            # Check that we can resolve those links, finding the python executable.
            self.assertTrue(os.path.exists(os.path.join(tmpdir, 'bleeding', 'next', 'bin', 'python')))

    def test_specified_env_labels(self):
        with resolve.tempdir() as tmpdir:
            deploy.deploy_repo(self.repo, tmpdir, ['default/next', 'bleeding/*'])

            self.assertTrue(self.check_link_exists(tmpdir, 'default', 'next'))
            self.assertTrue(self.check_link_exists(tmpdir, 'bleeding', 'next'))
            self.assertTrue(self.check_link_exists(tmpdir, 'bleeding', 'latest'))
            
            self.assertFalse(os.path.exists(os.path.join(tmpdir, 'default', 'current')))
            self.assertFalse(os.path.exists(os.path.join(tmpdir, 'default', 'latest')))


if __name__ == '__main__':
    unittest.main()
