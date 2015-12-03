import contextlib
import os
import textwrap
import unittest

from git import Repo
from conda_gitenv import resolve, tag_dates, label_tag, deploy
from conda_gitenv.tests.integration.setup_samples import create_repo


class Test_tags_by_env(unittest.TestCase):
    def setUp(self):
        self.repo = create_repo('env_tags')

    def assert_tagnamed(self, result, expected):
        # Converts tag instances to strings for easy testing.
        result_tag_name = {env: sorted(tag.name for tag in tags)
                           for env, tags in result.items()}
        self.assertEqual(result_tag_name, expected)

    def test_no_tags(self):
        r = deploy.tags_by_env(self.repo)
        self.assertEqual(r, {})

    def test_simple_tag(self):
        self.repo.create_tag('env-testing-abc')
        r = deploy.tags_by_env(self.repo)
        self.assert_tagnamed(r, {'testing': ['env-testing-abc']})

    def test_multiple_tags(self):
        self.repo.create_tag('env-testing2-1')
        self.repo.create_tag('env-testing1-2')
        self.repo.create_tag('env-testing1-1')
        r = deploy.tags_by_env(self.repo)
        self.assert_tagnamed(r, {'testing1': ['env-testing1-1', 'env-testing1-2'],
                                 'testing2': ['env-testing2-1']})


class Test_tags_by_label(unittest.TestCase):
    def test_no_tags(self):
        expected = {}
        with resolve.tempdir() as labels_dir:
            label_tag.write_labels(labels_dir, expected)
            result = deploy.tags_by_label(labels_dir)
        self.assertEqual(result, expected)

    def test_some(self):
        expected = {'a': '123', 'abc123': 'foobar-again'}
        with resolve.tempdir() as labels_dir:
            label_tag.write_labels(labels_dir, expected)
            result = deploy.tags_by_label(labels_dir)
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
