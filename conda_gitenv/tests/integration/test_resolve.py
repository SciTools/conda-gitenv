import contextlib
import os
import textwrap
import unittest
from subprocess import check_call

import conda_gitenv.tests.integration.setup_samples as setup_samples


class Test_full_build(unittest.TestCase):
    def check_env(self, name):
        repo = setup_samples.basic_repo(name)
        self.assertNotIn('manifest/master', repo.branches)
        check_call(['conda', 'gitenv', 'resolve', repo.working_dir])
        self.assertIn('manifest/master', repo.branches)
        manifest_branch = repo.branches['manifest/master']
        manifest_branch.checkout()
        with open(os.path.join(repo.working_dir, 'env.manifest'), 'r') as fh:
            env_manifest = fh.readlines()
            pkg_names = [pkg.split('\t', 1)[1].split('-')[0]
                         for pkg in env_manifest]
            self.assertIn('python', pkg_names)
            self.assertIn('zlib', pkg_names)
        return repo

    def test_env_basic(self):
        self.check_env('basic')

    def test_env_update(self):
        repo = self.check_env('update')
        master = repo.branches['master']
        spec = """
            env:
             - python
             - numpy
            channels:
             - defaults
            """
        comment = 'Update the env.spec'
        setup_samples.update_env(repo, master, spec, comment)
        self.assertIn('manifest/master', repo.branches)
        check_call(['conda', 'gitenv', 'resolve', repo.working_dir])
        manifest = repo.branches['manifest/master']
        manifest.checkout()
        with open(os.path.join(repo.working_dir, 'env.manifest'), 'r') as fh:
            env_manifest = fh.readlines()
            pkg_names = [pkg.split('\t', 1)[1].split('-')[0]
                         for pkg in env_manifest]
            self.assertIn('numpy', pkg_names)
        with open(os.path.join(repo.working_dir, 'env.spec'), 'r') as fh:
            env_spec = [entry.strip() for entry in fh.readlines()]
        self.assertIn('- numpy', env_spec)


if __name__ == '__main__':
    unittest.main()
