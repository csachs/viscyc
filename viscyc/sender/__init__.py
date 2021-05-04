import os
import sys
from pathlib import Path
from subprocess import Popen

import pkg_resources


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    script = Path(pkg_resources.resource_filename("viscyc.sender", "zwack-server.js"))

    current_dir = Path.cwd()

    try:
        os.chdir(str(script.parent))

        process = Popen(["node", str(script.name)] + args)

        process.wait()
    finally:
        process.kill()
        os.chdir(str(current_dir))
