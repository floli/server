import os, smtplib, socket, stat
from email.mime.text import MIMEText

def checkSSLKey(key, user):
    """ Checks if the SSL key are correct, sends email if not."""
    mode = key.stat().st_mode
    if (mode & stat.S_IRGRP) or (mode & stat.S_IROTH):
        os.chmod(key, stat.S_IRUSR | stat.S_IWUSR)
        localhost = socket.getfqdn()
        text = """Dear {user},
Your SSL key {key} had permissions that made it group and world readable. This was corrected and permissions were set to -rw-------. However, there was a time period when it was world readable.
Yours sincerely, root.""".format(user = user, key = key)
        msg = MIMEText(text)
        msg['Subject'] = "Security violation found for %s" % user
        msg['From'] = "root@%s" % localhost
        msg['To'] = user + "@" + localhost
        s = smtplib.SMTP('localhost')
        s.sendmail(msg['From'], msg['To'], msg.as_string())
        s.quit()

