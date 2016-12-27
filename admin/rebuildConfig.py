#!/usr/bin/env python3

import common, policyChecker
import os, pwd, glob

from string import Template
from pathlib import Path

   
def addAliases(domainname):
    """ Adds the reserved aliases for a given domain (e.g. hostmaster) to the table. """
    sql = "INSERT INTO {VIRTUAL_TBL} (virtual, alias) VALUES "
    args = []
    for name in common.ADMIN_ALIASES:
        sql += "(%s, 'root'), "
        args.append(name + "@" + domainname)
    sql = sql[:len(sql)-2]  # Remove the last kommata
    DB.sql(sql,  *args)

    
def getTemplate(file):
    with open(file, "r") as f:
        templateStr = f.read()
    return Template(templateStr)


def writeTemplate(inputTemplate, outputFile, **templateArgs):
    template = getTemplate(inputTemplate)
    output = template.substitute(templateArgs)
    with open(outputFile, "w") as f:
        f.write(output)

        
def rebuildAliases():
    """ Deletes all ALIASES and rebuilds them based on the entries from DOMAIN_TABLE. """
    for name in common.ADMIN_ALIASES:
        sql = "DELETE FROM {VIRTUAL_TBL} WHERE virtual LIKE '" + name + "@%'"
        DB.sql(sql)

    sql = "SELECT domain FROM {DOMAIN_TBL} WHERE mail = TRUE"
    retVal, domains = DB.sql(sql)
    # return should have only n rows with one field each.
    for dom in domains:
        domain = dom[0]
        sql = "INSERT INTO {VIRTUAL_TBL} (virtual, alias) VALUES "
        args = []
        for name in common.ADMIN_ALIASES:
            sql += "(%s, 'root'), "
            args.append(name + "@" + domain)
        sql = sql[:len(sql)-2]  # Remove the last kommata
        DB.sql(sql,  *args)

        
def hasSSL(domain, user):
    """ Returns if the SSL files are in place for a domain / user """
    cert, key = SSLfiles(domain, user)
    return cert.is_file() and key.is_file()


def SSLfiles(domain, user):
    """ Returns (sslcertificate, sslkey, chain) """
    cert   = Path("/home", user, domain, "ssl", domain + ".cert")
    key    = Path("/home", user, domain, "ssl", domain + ".key")
    return cert, key


def rebuildApacheConfig():
    """ Create the Apache config for all domains where http=True. Adds aliases. """
    retVal, resultSet = DB.sql("SELECT domain, user FROM {DOMAIN_TBL} WHERE http = TRUE")
    template = getTemplate("templates/apache-config.template")
    templateSSL = getTemplate("templates/apache-config-ssl.template")
    
    output = ""
    outputSSL = ""
    for row in resultSet:
        sql = "SELECT alias FROM {DOMAIN_ALIASES_TBL} WHERE domain = %s"
        retVal, aliases = DB.sql(sql, row[0])
        configAliases = ""
        for alias in aliases:
            configAliases += alias[0] + " *." + alias[0] + " "

        domain, user = row[0], row[1]
        if hasSSL(row[0], row[1]):
            cert, key = SSLfiles(domain, user)
            policyChecker.checkSSLKey(key, user)
            outputSSL += templateSSL.substitute(domain = domain, user = user,
                                                certfile = cert, keyfile = key, aliases = configAliases)
            outputSSL += "\n\n"
            
        output += template.substitute(domain = domain, user = user, aliases = configAliases)
        output += "\n\n"
    
    with open("output/generated-vhosts.conf", "w") as f:
        f.write(output)

    with open("output/generated-vhosts-ssl.conf", "w") as f:
        f.write(outputSSL)

    
def rebuildLogrotateConfig():
    retVal, resultSet = DB.sql("SELECT domain, user FROM {DOMAIN_TBL} WHERE http = TRUE")
    logs = ""
    for row in resultSet:
        logs += "/home/%s/%s/log/access.log \n" % (row[1], row[0])
        logs += "/home/%s/%s/log/error.log \n" % (row[1], row[0])

    writeTemplate("templates/logrotate-config.template", "output/generated-logrotate.conf", logs = logs.rstrip())

    
def rebuildAwstatsConfig():
    build_command = ""
    retVal, resultSet = DB.sql("SELECT domain, user FROM {DOMAIN_TBL} WHERE http_statistics = TRUE")
    for row in resultSet:
        domain, user = row[0], row[1]
        retVal, alResult = DB.sql("SELECT alias FROM {DOMAIN_ALIASES_TBL} WHERE domain = %s", domain)
        aliasesList = [n[0] for n in alResult]
        aliases = " ".join(aliasesList)
        writeTemplate("templates/awstats-config.template", "output/awstats." + domain + ".conf", domain = domain, user = user, aliases = aliases)
#        build = '/usr/share/awstats/tools/awstats_buildstaticpages.pl -config="%s" -lang="de" -dir="/home/%s/%s/statistics/" -awstatsprog="/opt/awstats-6.95/wwwroot/cgi-bin/awstats.pl"'
        build_command += '/usr/share/awstats/tools/awstats_buildstaticpages.pl -config="{domain}" -lang="de" -dir="/home/{user}/{domain}/statistics/" \n'
        build_command += 'mv "/home/{user}/{domain}/statistics/awstats.{domain}.xml" "/home/{user}/{domain}/statistics/index.html" \n \n'
        build_command = build_command.format(user = user, domain = domain)
        
    writeTemplate("templates/awstats-build.sh.template", "output/awstats-build.sh", build_command = build_command)
        

def test_and_create(path, user):
     """ Tests if a directory exists, if not creates it with 0700. """
     if not os.access(path, os.F_OK):
         os.mkdir(path, 0o700)
         uid = pwd.getpwnam(user).pw_uid
         gid = pwd.getpwnam(user).pw_gid
         os.chown(path, uid, gid)
         print("Created:", path)
         print("Username, UID, GID:", user, uid, gid)
         print("")
 
    
def addDomainDirs():
    retVal, resultSet = DB.sql("SELECT domain, user, http_statistics FROM {DOMAIN_TBL} WHERE http = TRUE")
    for row in resultSet:
        domain = row[0]
        user = row[1]
        stats = row[2]
        path = "/home/%s/%s/" % (user, domain)
        test_and_create(path, user)
        test_and_create(path + "pub/", user)
        test_and_create(path + "log/", user)
        test_and_create(path + "tmp/", user)
        test_and_create(path + "ssl/", user)
        if stats:
            test_and_create(path + "statistics/", user)
   
from shutil import move
 
def moveFiles():
    move("output/generated-vhosts.conf", "/etc/apache2/sites-available/generated-vhosts.conf")
    move("output/generated-vhosts-ssl.conf", "/etc/apache2/sites-available/generated-vhosts-ssl.conf")
    move("output/generated-logrotate.conf", "/etc/logrotate.d/generated-logrotate.conf") 
    move("output/awstats-build.sh", "/usr/local/bin/awstats-build.sh")
    Path("/usr/local/bin/awstats-build.sh").chmod(0o755)

    # Remove previous awstats files
    awstats_dir = Path("/etc/awstats/")
    for f in awstats_dir.glob("awstats.*.*.conf"):
        f.unlink()

    for f in Path("./output").glob("awstats.*.*.conf"):
        f.rename(awstats_dir / f.name)

import subprocess

def restartServices():
    """ Restart services to get the new config, at the moment this is only apache. """
    try:
        subprocess.check_output("apachectl configtest", shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        body = "Error from apache2ctl configtest. Returncode was %i.\n\n" % e.returncode + e.output
        common.mailRoot(body, "Error from apache2ctl configtest")
        print(body)
    else:
        print("Restarting apache.")
        subprocess.check_call("systemctl try-reload-or-restart apache2", shell=True)

DB = common.DB()

def main():
    rebuildLogrotateConfig()
    rebuildApacheConfig()
    rebuildAliases()
    addDomainDirs() # Creates the directories in every users home
    rebuildAwstatsConfig()
    moveFiles()
    restartServices()

if __name__ == "__main__":
    main()
