#!env python3

""" Syncs the home dirs as long as there is no STOP_SYNC file present. """

import os, subprocess, sys
from pathlib import Path

EXCLUDE = ["ftp", "backup"]

lock = Path("/home/sync.lock")

os.chdir("/home")

if lock.exists():
    print("Lock file exists.")
    sys.exit(0)

lock.touch()

for path in Path(".").iterdir():
    if path.is_dir() and path.name not in EXCLUDE and not (path / "STOP_SYNC").is_file():
        cmd = "rsync -avz --delete root@astarte.centershock.net:/home/{dir}/ /home/{dir}".format(dir = path)
        print(cmd)
        subprocess.check_call(cmd, shell=True)

lock.unlink()

        
