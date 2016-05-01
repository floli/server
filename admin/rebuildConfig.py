import common, policyChecker
import os, pwd, glob

from string import Template

   
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
    f = open(file, "r")
    templateStr = f.read()
    f.close()
    return Template(templateStr)

def writeTemplate(inputTemplate, outputFile, **templateArgs):
    template = getTemplate(inputTemplate)
    output = template.substitute(templateArgs)
    f = open(outputFile, "w")
    f.write(output)
    f.close()
    
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
    cert, key, chain = SSLfiles(domain, user)
    return os.path.isfile(cert) and os.path.isfile(key)

def SSLfiles(domain, user):
    """ Returns (sslcertificate, sslkey, chain) """
    cert   = os.path.join("/home", user, domain, "ssl", domain + ".cert")
    key    = os.path.join("/home", user, domain, "ssl", domain + ".key")
    chain  = os.path.join("/home", user, domain, "ssl/chain.pem")
    return cert, key, chain
        
def rebuildApacheConfig():
    """ Create the Apache config for all domains where http=True. Adds aliases. """
    retVal, resultSet = DB.sql("SELECT domain, user FROM {DOMAIN_TBL} WHERE http = TRUE")
    template = getTemplate("apache-config.template")
    templateSSL = getTemplate("apache-config-ssl.template")
    
    output = ""
    outputSSL = ""
    for row in resultSet:
        sql = "SELECT alias FROM {HTTP_ALIASES_TBL} WHERE domain = %s"
        retVal, aliases = DB.sql(sql, row[0])
        configAliases = ""
        for alias in aliases:
            configAliases += alias[0] + " *." + alias[0] + " "

        domain, user = row[0], row[1]
        if hasSSL(row[0], row[1]):
            cert, key, chain = SSLfiles(domain, user)
            chain_statement =  "SSLCertificateChainFile " + chain if os.path.isfile(chain) else ""
            policyChecker.checkSSLKey(key, user)
            outputSSL += templateSSL.substitute(domain = domain, user = user,
                                                certfile = cert, keyfile = key,aliases = configAliases,
                                                chainfile = chain_statement)
            
        output += template.substitute(domain = domain, user = user, aliases = configAliases)
        output += "\n\n"
    
    f = open("generated-vhosts", "w")
    f.write(output)
    f.close()

    f = open("generated-vhosts-ssl", "w")
    f.write(outputSSL)
    f.close
    
def rebuildSSLPRoxy():
    retVal, resultSet = DB.sql("SELECT domain FROM {DOMAIN_TBL} WHERE http = TRUE")
    template = getTemplate("sslproxy-config.template")
    
    output = ""
    for row in resultSet:
        output += template.substitute(domain = row[0])
        output += "\n"

    f = open("sslproxy.conf", "w")
    f.write(output)
    f.close()
    
def rebuildLogrotateConfig():
    retVal, resultSet = DB.sql("SELECT domain, user FROM {DOMAIN_TBL} WHERE http = TRUE")
    logs = ""
    for row in resultSet:
        logs += "/home/%s/%s/log/access.log \n" % (row[1], row[0])
        logs += "/home/%s/%s/log/error.log \n" % (row[1], row[0])

    writeTemplate("logrotate-config.template", "generated-logrotate.conf", logs = logs.rstrip())
    

    
def rebuildAwstatsConfig():
    buildCommand = ""
    retVal, resultSet = DB.sql("SELECT domain, user FROM {DOMAIN_TBL} WHERE http_statistics = TRUE")
    for row in resultSet:
        domain, user = row[0], row[1]
        retVal, alResult = DB.sql("SELECT alias FROM {HTTP_ALIASES_TBL} WHERE domain = %s", domain)
        aliasesList = [n[0] for n in alResult]
        aliases = " ".join(aliasesList)
        writeTemplate("awstats-config.template", "awstats." + domain + ".conf", domain = domain, user = user, aliases = aliases)
        build = '/opt/awstats-6.95/tools/awstats_buildstaticpages.pl -config="%s" -lang="de" -dir="/home/%s/%s/statistics/" -awstatsprog="/opt/awstats-6.95/wwwroot/cgi-bin/awstats.pl"'
        buildCommand += "\n" + build % (domain, user, domain)
        build = 'mv "/home/%s/%s/statistics/awstats.%s.html" "/home/%s/%s/statistics/index.html"' % (user, domain, domain, user, domain)
        buildCommand += "\n" + build
    writeTemplate("rotate_and_report.template", "rotate_and_report", build_command = buildCommand)
        

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
    move("generated-vhosts", "/etc/apache2/sites-available/generated-vhosts")
    move("generated-vhosts-ssl", "/etc/apache2/sites-available/generated-vhosts-ssl")
    move("generated-logrotate.conf", "/etc/logrotate.d/generated-logrotate.conf")
    move("sslproxy.conf", "/etc/apache2/sslproxy.conf")
    move("rotate_and_report", "/etc/cron.daily/rotate_and_report")
    os.chmod("/etc/cron.daily/rotate_and_report", 0o755)

    # Remove previous awstats files
    # files = glob.glob("/etc/awstats/awstats.*.*.conf")
    # for f in files: os.remove(f)

    # filesToMove = glob.glob("awstats.*.*.conf")
    # for f in filesToMove:
    #     move(f, "/etc/awstats/" + f)

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
        subprocess.check_call("service apache2 reload", shell=True)

DB = common.DB()

def main():
    rebuildLogrotateConfig()
    rebuildApacheConfig()
    rebuildSSLPRoxy()
    rebuildAliases()
    addDomainDirs() # Creates the directories in every users home
    rebuildAwstatsConfig()
    moveFiles()
    restartServices()

if __name__ == "__main__":
    main()
