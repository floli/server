#!/usr/bin/python2

import email, email.utils, sys
import os.path, subprocess

"""
Example for .mailfilter:

if ($ADR eq "mailinglists@centershock.net")
{
        xfilter "~/detect_maillist.py"
	if (/^X-Target-Folder: (.*)$/) 
	{
	   to "$MDIR/$ADR/.$MATCH1"   # Mind the dot!
	}
	to "$MDIR/$ADR"
}
"""


# Dictionary of listname => folder mappings. Can be used to overwrite the heuristic.
known_lists = {
    # "scipy-user.scipy.org" : "scipy-user",
}

# Base Maildir in which the subfolders are crated
MDIR = "mailinglists@centershock.net"

# Headers to get the listname from, in ordner.
headers = ["X-Mailing-List", "List-Id", "List-ID"]


def get_foldername(listname):
    """ Construct/guess a suitable foldername for a list. """
    if listname in known_lists:
        listname = known_lists[listname]
    elif "@" in listname:
        listname = listname.split("@")[0]
    else:
        listname = listname.split(".")[0]

    listname = listname.replace(".", "-") # . works as path seperator in IMAP
    return listname


# Better be sure about relative paths
MDIR = os.path.expanduser(os.path.join("~", "Mail", MDIR))

msg = email.message_from_file(sys.stdin)

# Get value from first found header
for h in headers:
    listname = msg[h]
    if listname != None:
        break

# No header found, Exit.
if listname == None:
    sys.stdout.write(msg.as_string())
    sys.exit(0)

listname = email.utils.parseaddr(listname)[1]
foldername = get_foldername(listname)

# Some logging
f = open("detect_maillist.log", "a")
f.write(listname + " => " + foldername + "\n")


# Create dir using maildirmake, if not existing
if not os.path.isdir(os.path.join(MDIR, "." + foldername)):
    subprocess.Popen( ["maildirmake", "-f", foldername, MDIR] )
    f.write("Created Dir: " + foldername + "\n")

f.close()

# This is for maildrop or another MDA.
msg["X-Target-Folder"] = foldername

# Don't forget that, otherwise mail will be lost.
sys.stdout.write(msg.as_string())


