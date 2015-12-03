from setuptools import setup


setup(
      name='conda-gitenv',
      version='0.1.0',
      description='Track environment specifications using a git repo.',
      author='Phil Elson',
      author_email='pelson.pub@gmail.com',
      url='https://github.com/scitools/conda-gitenv',
      packages=['conda_gitenv'],
      entry_points={
          'console_scripts': [
              'conda-gitenv = conda_gitenv.cli:main',
              'conda-env-tracker = conda_gitenv.resolve:main',
              'conda-env-tracker-timestamp = conda_gitenv.tag_dates:main',
              'conda-env-tracker-labeltag = conda_gitenv.label_tag:main',
              'conda-env-tracker-deploy = conda_gitenv.deploy:main',
          ]
      },
     )

