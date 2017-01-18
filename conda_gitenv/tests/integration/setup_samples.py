import os
import textwrap
import shutil

from git import Repo


SAMPLE_REPOS = os.path.join(os.path.dirname(__file__), 'sample_repos')


def create_repo(name):
    repo_dir = os.path.join(SAMPLE_REPOS, name)
    if os.path.exists(repo_dir):
        shutil.rmtree(repo_dir)
    repo = Repo.init(repo_dir)
    repo.index.commit('Initial commit.')
    return repo


def add_env(repo, name, spec):
    branch = repo.create_head(name)
    update_env(repo, branch, spec)
    return branch


def update_env(repo, branch, spec, comment=None):
    branch.checkout()
    env_spec = os.path.join(repo.working_dir, 'env.spec')
    with open(env_spec, 'w') as fh:
        fh.write(textwrap.dedent(spec))
    repo.index.add([env_spec])
    if comment is None:
        comment = 'Add {} spec'.format(branch.name)
    repo.index.commit(comment)


def basic_repo():
    # The simplest kind of repo. One env defined under the name "master"
    repo = create_repo('basic')
    branch = add_env(repo, 'master', """
        env:
         - python
        channels:
         - defaults 
        """)
    return repo


def main():
    basic_repo()


if __name__ == '__main__':
    main()
