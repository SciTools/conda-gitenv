from setuptools import setup


setup(
      name='conda-env-tracker',
      version='0.1.0',
      description='Track environment specifications using a git repo.',
      author='Phil Elson',
      author_email='pelson.pub@gmail.com',
      url='https://github.com/scitools/conda-env-tracker',
      packages=['conda_env_tracker'],
      entry_points={
          'console_scripts': [
              'conda-gitenv = conda_env_tracker.cli:main',
              'conda-env-tracker = conda_env_tracker.resolve:main',
              'conda-env-tracker-timestamp = conda_env_tracker.tag_dates:main',
              'conda-env-tracker-labeltag = conda_env_tracker.label_tag:main',
              'conda-env-tracker-deploy = conda_env_tracker.deploy:main',
          ]
      },
     )

