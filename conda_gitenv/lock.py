import os

import conda.lock


# Propose as an enhancement to conda. This would be in order to be more specific with conda's lock files.
class Locked(conda.lock.Locked):
    def __init__(self, directory_to_lock):
        """
        Lock the given directory for use, unlike conda.lock.Lock which
        locks the directory passed, meaning you have to come up with another
        name for the directory to lock.

        """
        dirname, basename = os.path.split(directory_to_lock.rstrip(os.pathsep))
        path = os.path.join(dirname, '.conda-lock_' + basename)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        return conda.lock.Locked.__init__(self, path)
