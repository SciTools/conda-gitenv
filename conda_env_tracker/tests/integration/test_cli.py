import contextlib
import os
import textwrap
import unittest
from subprocess import check_call

import setup_samples


class Test_full_build(unittest.TestCase):
    def test_basic_env(self):
        repo = setup_samples.basic_repo()
        self.assertNotIn('manifest/master', repo.branches)
        check_call(['conda-env-tracker', repo.working_dir])
        self.assertIn('manifest/master', repo.branches)
        manifest_branch = repo.branches['manifest/master']
        manifest_branch.checkout()
        with open(os.path.join(repo.working_dir, 'env.manifest'), 'r') as fh:
            manifest_contents = fh.readlines()
            pkg_names = [pkg.split('-', 1)[0] for pkg in manifest_contents]
            self.assertIn('python', pkg_names)
            self.assertIn('zlib', pkg_names)

if __name__ == '__main__':
    unittest.main()
