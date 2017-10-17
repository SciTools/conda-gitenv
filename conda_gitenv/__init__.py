from __future__ import absolute_import, division, print_function, unicode_literals

from conda import __version__ as CONDA_VERSION

from ._version import get_versions


def _parse_conda_version_major_minor(string):
    return string and tuple(int(x) for x in (string.split('.') + [0, 0])[:2]) or (0, 0)


__version__ = get_versions()['version']
del get_versions

CONDA_VERSION_MAJOR_MINOR = _parse_conda_version_major_minor(CONDA_VERSION)
conda_43 = CONDA_VERSION_MAJOR_MINOR >= (4, 3)
assert conda_43, 'Minimum supported conda version is {}.{}'.format(*CONDA_VERSION_MAJOR_MINOR)

manifest_branch_prefix = 'manifest/'
