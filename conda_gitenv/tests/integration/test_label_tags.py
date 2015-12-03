import contextlib
import os
import textwrap
import unittest
from subprocess import check_call

import setup_samples
from conda_gitenv.tag_dates import tag_by_branch


class Test_cli(unittest.TestCase):
    def test(self):
        repo = setup_samples.create_repo('labelled_tags')

        tag1 = 'env-example_env-1971_02_28'
        tag2 = 'env-example_env-1972_03_31'
        tag3 = 'env-example_env-1973_05_31'
        tag4 = 'env-example_env-1974_05_31'

        branch = repo.create_head('example_env')
        manifest_branch = repo.create_head('manifest/example_env')
        repo.create_tag(tag1, manifest_branch)

        labels_dir = os.path.join(repo.working_dir, 'labels')
        next_fname = os.path.join(labels_dir, 'next.txt')
        prev_fname = os.path.join(labels_dir, 'previous.txt')
        current_fname = os.path.join(labels_dir, 'current.txt')

        branch.checkout()
        self.assertFalse(os.path.exists(labels_dir))
        # Checkout a different branch so that we can checkout the changes later on.
        manifest_branch.checkout()
        check_call(['conda-env-tracker-labeltag', repo.working_dir, tag1])

        branch.checkout()
        self.assertTrue(os.path.exists(labels_dir))

        with open(next_fname, 'r') as fh:
            next_label = fh.read()
        self.assertEqual(next_label, tag1)
        self.assertFalse(os.path.exists(prev_fname))
        self.assertFalse(os.path.exists(current_fname))

        # Now add another tag, and move it through the process.
        repo.create_tag(tag2, manifest_branch)
        manifest_branch.checkout()
        check_call(['conda-env-tracker-labeltag', repo.working_dir, tag2])

        branch.checkout()
        with open(next_fname, 'r') as fh:
            next_label = fh.read()
        self.assertEqual(next_label, tag2)
        with open(current_fname, 'r') as fh:
            current_label = fh.read()
        self.assertEqual(current_label, tag1)
        self.assertFalse(os.path.exists(prev_fname))

        # Now add another tag, but only update the "next" label..
        repo.create_tag(tag3, manifest_branch)
        manifest_branch.checkout()
        check_call(['conda-env-tracker-labeltag', repo.working_dir, tag3, '--next-only'])

        branch.checkout()
        with open(next_fname, 'r') as fh:
            next_label = fh.read()
        self.assertEqual(next_label, tag3)
        with open(current_fname, 'r') as fh:
            current_label = fh.read()
        self.assertEqual(current_label, tag1)
        self.assertFalse(os.path.exists(prev_fname))

        # Now add another tag, and move it through the process.
        repo.create_tag(tag4, manifest_branch)
        manifest_branch.checkout()
        check_call(['conda-env-tracker-labeltag', repo.working_dir, tag4])

        branch.checkout()
        with open(next_fname, 'r') as fh:
            next_label = fh.read()
        self.assertEqual(next_label, tag4)
        with open(current_fname, 'r') as fh:
            current_label = fh.read()
        self.assertEqual(current_label, tag3)
        with open(prev_fname, 'r') as fh:
            prev_label = fh.read()
        self.assertEqual(prev_label, tag1)


if __name__ == '__main__':
    unittest.main()
