from __future__ import absolute_import, division, print_function, unicode_literals

from distutils.version import StrictVersion

from conda import __version__ as CONDA_VERSION

from ._version import get_versions


__version__ = get_versions()['version']
del get_versions

_conda_base = StrictVersion('4.3.0')
_conda_support = StrictVersion(CONDA_VERSION) >= _conda_base
assert _conda_support, 'Minimum supported conda version is {}.'.format(_conda_base)

manifest_branch_prefix = 'manifest/'
