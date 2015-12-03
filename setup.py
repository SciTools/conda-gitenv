from setuptools import setup
import versioneer


setup(
      name='conda-gitenv',
      version=versioneer.get_version(),
      cmdclass=versioneer.get_cmdclass(),
      description='Track environment specifications using a git repo.',
      author='Phil Elson',
      author_email='pelson.pub@gmail.com',
      url='https://github.com/scitools/conda-gitenv',
      packages=['conda_gitenv', 'conda_gitenv.tests',
                'conda_gitenv.tests.unit', 'conda_gitenv.tests.integration'],
      entry_points={
          'console_scripts': [
              'conda-gitenv = conda_gitenv.cli:main',
          ]
      },
     )

