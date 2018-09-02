import os, stat
from common import mail_user

def checkSSLKey(key, user):
    """ Checks if the SSL key are correct, sends email if not."""
    mode = key.stat().st_mode
    if (mode & stat.S_IRGRP) or (mode & stat.S_IROTH):
        key.chmod(stat.S_IRUSR | stat.S_IWUSR)
        text = """Dear {user},
Your SSL key {key} had permissions that made it group and world readable. This was corrected and permissions were set to -rw-------. However, there was a time period when it was world readable.
Yours sincerely, root.""".format(user = user, key = key)
        mail_user(user, "Security violation found for %s" % user, text)
