#!/usr/bin/python2

import email, email.utils, re, sys
import os.path, subprocess

"""
This script reads an email from standard input and scans for headers indicating it is from a mailing list.
If so, a corresponding maildir folder is created in MDIR and a X-Target-Folder is added to the message.

This header can be read out by an MDA (Mail Delivery Agent). Example for Courier Maildrop .mailfilter:

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

# Base Maildir in which the subfolders are created, relative to your HOME.
MDIR = "Mail/mailinglists@centershock.net"

# Dictionary of listname => folder mappings. Can be used to overwrite the heuristic.
known_lists = {
    "users@spamassassin.apache.org" : "spamassassin",
}

# Dictionary of headers that need special treatment for listname extraction
# First match group of regular expresion is taken. email.utils.parseaddr will still be applied on match
known_headers = {
    "List-Post" : r"<mailto:(.*)>"  # Matches e.g. "<mailto:postfix-users@postfix.org>" as seen on Majordomo lists
}

# Names that are invalid for folders. 
# If a target folder with a such a name is generated, the mail is not treated as list post.
invalid_names = ["users", "mailman"]


# Headers to get the listname from, in order.
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
MDIR = os.path.expanduser(os.path.join("~", MDIR))

msg = email.message_from_file(sys.stdin)

# Get value from first found header
for h in known_headers.keys() + headers:
    listname = msg[h]
    if listname != None:
        break

# Use the regexp to extract the listname from the header, if found.
if h in known_headers and listname != None:
    try:
        listname = re.match(known_headers[h], listname).groups()[0]
    except AttributeError:
        listname = None

# No header found, Exit.
if listname == None:
    sys.stdout.write(msg.as_string())
    sys.exit(0)

listname = email.utils.parseaddr(listname)[1]
foldername = get_foldername(listname)

# Foldername is invalid, Exit.
if foldername in invalid_names:
    sys.stdout.write(msg.as_string())
    sys.exit(0)

# Some logging
# f = open("detect_maillist.log", "a")
# f.write(listname + " => " + foldername + "\n")

# Create dir using maildirmake, if not existing
if not os.path.isdir(os.path.join(MDIR, "." + foldername)):
    subprocess.Popen( ["maildirmake", "-f", foldername, MDIR] )
    # f.write("Created Dir: " + foldername + "\n")

# f.close()

# This is for maildrop or another MDA.
msg["X-Target-Folder"] = foldername

# Don't forget that, otherwise mail will be lost.
sys.stdout.write(msg.as_string())


