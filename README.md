Track environment specifications using a git repo
-------------------------------------------------

``conda gitenv`` is a designed to simplify the deployment centrally managed conda environments.
Rather than expecting a sysadimn to administer appropriate conda commands on a live system, it decouples
the ``conda update`` phase from the actual deployment, giving users the ability to review and prepare for
any forthcoming changes.

This decoupling is achieved by defining a series of environments in the form of a git repository. Any changes to
the environment are therefore achieved by making changes to the repository - typically in the form of pull requests.

We start by creating an empty repository, with the name of the branch being the name of the environment, and a
``env.spec`` file being the loose definition of the environment.

```
export ENV_REPO=${HOME}/environments
mkdir -p ${ENV_REPO} && cd ${ENV_REPO}
git init
git checkout -b default
cat <<EOF > env.spec
channels:
 - defaults
 env: 
 - python

EOF

git add env.spec
git commit -m "Added the default environment."

```

The update process can be broken into multiple phases, any/all of which can potentially be fully automated.


Phase 1: Resolve the environment (manifestication)
==================================================

First, we resolve the ``env.spec`` from each of the branches in the repo (in this case, we just have a branch named ``default``). 

```
$ conda gitenv resolve ${ENV_REPO}
Pushing changes to manifest/default
```

This will create a ``manifest/default`` branch in the repo, let's take a look at the result:

```
$ git checkout manifest/default
$ cat env.manifest 
https://repo.continuum.io/pkgs/free/linux-64/   openssl-1.0.2d-0
https://repo.continuum.io/pkgs/free/linux-64/   pip-7.1.2-py35_0
https://repo.continuum.io/pkgs/free/linux-64/   python-3.5.0-1
https://repo.continuum.io/pkgs/free/linux-64/   readline-6.2-2
https://repo.continuum.io/pkgs/free/linux-64/   setuptools-18.4-py35_0
https://repo.continuum.io/pkgs/free/linux-64/   sqlite-3.8.4.1-1
https://repo.continuum.io/pkgs/free/linux-64/   tk-8.5.18-0
https://repo.continuum.io/pkgs/free/linux-64/   wheel-0.26.0-py35_1
https://repo.continuum.io/pkgs/free/linux-64/   xz-5.0.5-0
https://repo.continuum.io/pkgs/free/linux-64/   zlib-1.2.8-0
```

(Note: Results will vary based on what packages are available at the time of running the command)

As you can see, our simple "python" ``env.spec`` has resulted in an ``env.manifest`` which includes python
(3.5.0 in this case) along with all of the necessary dependencies for creating a working Python environment
with conda.


Phase 2: Tag the manifest branches (timestamp)
==============================================

Once we are happy with the ``env.manifest``, it is time to tag the environment.
We can choose to automate the process using ``conda gitenv autotag``, which simply tags the head of each
environment (aka. branch) based on the last commit date.


```
$ conda gitenv autotag ${ENV_REPO}
Pushing tag env-default-2015_11_12
```

We now have a new tag on the repo which points to the latest commit on ``manifest/default``.

Phase 3: Deploy the environment(s)
==================================

With the repo in this form we have a single environment (named "default") with a single tag (in our case, "env-default-2015_11_12").
There is now sufficient information to deploy the repository of environments:

```
$ conda gitenv deploy ${ENV_REPO} /path/to/install/environments
Fetching package metadata: .
Fetching openssl-1.0.2d-0
Fetching pip-7.1.2-py35_0
Fetching python-3.5.0-1
Fetching readline-6.2-2
Fetching setuptools-18.4-py35_0
Fetching sqlite-3.8.4.1-1
Fetching tk-8.5.18-0
Fetching wheel-0.26.0-py35_1
Fetching xz-5.0.5-0
Fetching zlib-1.2.8-0
Linking default/latest to env-default-2015_11_12
```

If we investigate the install destination, we find that there is a directory called "default" which contains our tagged environment:

```
$ ls -ltr /path/to/install/environments/default
drwxr-xr-x pelson 4096 Nov 12 10:54 2015_11_12
lrwxrwxrwx pelson   10 Nov 12 10:54 latest -> 2015_11_12
```

Additionally, we've gained a ``latest`` "label" which is just a symbolic link to the newest tag for this environment. Additional
labels can be defined as part of the environment specification branch (details in phase 4).

Rinse and repeat
================

The environment defined in our default branch would result in a different ``env.manifest`` when newer packages become
available, so the phases can be repeated to update the deployed environment. Additionally we can add more environments
using the mechanisms we have already seen.

Let's assume we wish to include numpy in our default environment:

```
$ git checkout default
$ cat <<EOF > env.spec
channels:
 - defaults
env:
 - python
 - numpy

EOF

$ git add env.spec
$ git commit -m "Updated the default environment to include numpy."
```

And wish to provide an environment with legacy python:

```
$ git checkout -b legacy
$ cat <<EOF > env.spec
channels:
 - defaults
env:
 - python 2.*
 - numpy

EOF

$ git add env.spec
$ git commit -m "Created a 'legacy' environment for py2k."
```

We can now resolve our ``env.spec`` definitions (phase 1):

```
$ conda gitenv resolve ${ENV_REPO}
Pushing changes to manifest/default
Pushing changes to manifest/legacy
```

Tag the newly resolved environments (phase 2):

```
$ conda gitenv autotag ${ENV_REPO}
Pushing tag env-default-2015_11_12-1
Pushing tag env-legacy-2015_11_12
```

And deploy (phase 3):

```
$ conda gitenv deploy ${ENV_REPO} /path/to/install/environments
Fetching package metadata: .
Fetching libgfortran-1.0-0
Fetching numpy-1.10.1-py35_0
Fetching openblas-0.2.14-3
Linking default/latest to env-default-2015_11_12-1
Fetching numpy-1.10.1-py27_0
Fetching pip-7.1.2-py27_0
Fetching python-2.7.10-2
Fetching setuptools-18.4-py27_0
Fetching wheel-0.26.0-py27_1
Linking legacy/latest to env-legacy-2015_11_12
```

Finally, we can see that our environments have been deployed as expected:

```
$ ls -ltr /path/to/install/environments/*
/path/to/install/environments/defaults:
drwxr-xr-x pelson 4096 Nov 12 10:54 2015_11_12
drwxr-xr-x pelson 4096 Nov 12 11:31 2015_11_12-1
lrwxrwxrwx pelson   12 Nov 12 11:31 latest -> 2015_11_12-1

/path/to/install/environments/legacy:
drwxr-xr-x pelson 4096 Nov 12 11:32 2015_11_12
lrwxrwxrwx pelson   10 Nov 12 11:32 latest -> 2015_11_12
```

And can verify that we have the Python we expected:

```
$ /path/to/install/environments/latest/bin/python --version
Python 2.7.10
```

Phase 4: More labels (labeltag)
===============================

As environments evolve it is desirable to be able to label those of value.

As we have already seen, the "latest" label is automatically added to point to the
tag which points to the most recent commit. Labelled environments are implemented as
symlinks which point to the appropriate tag at deploy time.

It is possible to add other labels which point to tagged environments. Labels are currently
defined in the environment definition branch, under a directory called labels. For instance, to
add a "pre-prod" label to our default environment definition:

```
git checkout default
mkdir labels
echo "env-default-2015_11_12-1" > labels/pre-prod.txt
git add labels
git commit -am "Added a pre-prod label."
```

Re-running the deployment will see a new symbolic linked environment, pointing to the appropriate tag.

There is some machinery which helps us move through a next -> current -> previous workflow, but this is
likely to change in the future. Please raise an issue if you would like more detail on this.

Notes
-----

* If using ``conda gitenv`` on a local git repository, it will not be possible to push changes to a branch which is checked out.
  In these situations it is safest to put your local repo into "detached head" mode (one option ``git checkout --detach``).

* Assumes a basic approach of merge and fix, rather than verify before merge. To mitigate this concern, the labels concept allows
  us to point to a tag, which would not break if we merged something erroneously.



