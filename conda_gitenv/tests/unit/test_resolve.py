import contextlib
import os
import textwrap
import unittest

try:
    from io import StringIO
except ImportError:
    from StringIO import StringIO

import conda.resolve

from conda_gitenv.resolve import resolve_spec, tempdir
from conda_build_all.tests.unit import dummy_index


class Test_resolve_spec(unittest.TestCase):
    @contextlib.contextmanager
    def env_spec_fh(self, spec):
        with tempdir('env_spec') as tmpdir:
            fpath = os.path.join(tmpdir, 'env.spec')
            with open(fpath, 'w') as fh:
                fh.write(textwrap.dedent(spec))
            with open(fpath) as fh:
                yield fh

    def test(self):
        # Check that resolve_spec is returning the expected content.
        index = dummy_index.DummyIndex()
        index.add_pkg('foo', '2.7.0', depends=('bar',))
        index.add_pkg('foo', '3.5.0', depends=('bar',))
        index.add_pkg('bar', '1.2')

        with tempdir() as tmp:
            channel = index.write_to_channel(tmp)
            with self.env_spec_fh("""
                                channels:
                                    - file://{}
                                env:
                                    - foo
                                """.format(tmp)) as specfile:
                pkgs = resolve_spec(specfile)
        pkg_names = [line.split('\t')[-1] for line in pkgs]
        self.assertEqual(sorted(pkg_names), ['bar-1.2-0', 'foo-3.5.0-0'])

    def test_unresolvable(self):
        # Check there is no "defaults" being used. We assume that Python will
        # always be available in defaults.
        with self.env_spec_fh("""
                                channels: []
                                env:
                                    - python
                                """) as specfile:
            with self.assertRaises(conda.resolve.NoPackagesFound):
                pkgs = resolve_spec(specfile)


if __name__ == '__main__':
    unittest.main()
