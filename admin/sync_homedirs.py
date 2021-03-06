#!env python3

""" Syncs the home dirs as long as there is no STOP_SYNC file present. """

import datetime, os, subprocess, sys
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
        try:
            subprocess.check_call(cmd, shell=True, stdout = subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            if e.returncode == 24:
                pass
            else:
                raise e
        
        with (path / "LAST_SYNC").open("w") as f:
            f.write(datetime.datetime.now().isoformat(sep = " ") + "\n")


lock.unlink()
