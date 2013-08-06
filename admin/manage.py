from getopt import getopt
from os import sys
import MySQLdb

from common import *

def genUsername(domainname):
    return domainname.replace(".","")

def addDomain(domainname):
    sql = "INSERT INTO " + DOMAIN_TABLE + " (" + DOMAIN_FIELD + ") VALUES (%s)" 
    executeSQL(sql, domainname)

def delDomain(domainname):
    sql = "DELETE FROM " + DOMAIN_TABLE + " WHERE " + DOMAIN_FIELD + " = %s"
    executeSQL(sql, domainname)
    
def addUser(domainname, realname):
    username = genUsername(domainname)
    cmd = "adduser --disabled-password --gecos '%s' %s" % (realname, username)
    print cmd

def delUser(domainname):
    username = genUsername(domainname)
    cmd = "deluser %s" % (username)
    print cmd
    
def addAliases(domainname):
    sql = "INSERT INTO " + VIRTUAL_TABLE + " (virtual, alias) VALUES "
    paras = []
    for name in ALIASES:
        sql += "(%s, 'root'), "
        paras.append(name + "@" + domainname)
    sql = sql[:len(sql)-2]  # Remove the last kommata
    executeSQL(sql,  *paras)
    
def delAliases(domainname):
    for name in ALIASES:
        sql = "DELETE FROM " + VIRTUAL_TABLE + " WHERE virtual = %s" 
        executeSQL(sql, name + "@" + domainname )

def rebuildAliases():
    """ Deletes all ALIASES and rebuilds them based on the entries from DOMAIN_TABLE. """
    import pdb; pdb.set_trace()
    
    for name in ALIASES:
        sql = "DELETE FROM " + VIRTUAL_TABLE + " WHERE virtual LIKE '" + name + "@%'"
        executeSQL(sql)
    
    sql = "SELECT " + DOMAIN_FIELD + " FROM " + DOMAIN_TABLE
    retVal, domains = executeSQL(sql)
    # return should have only n rows with one field each.
    for dom in domains:
        addAliases(dom[0])
    
conn = None

def main():
    DBopen()
    
    optlist, args = getopt(sys.argv[1:], "adr")
    
    if optlist[0][0] == "-r":
        rebuildAliases()
        sys.exit(0)
    
    if len(optlist) != 1 or len(args) != 2:
        print "Wrong argument count!"
        sys.exit(-1)
    
    if optlist[0][0] == "-a":
        action = "add"
    elif optlist[0][0] == "-d":
        action ="del"
    
    domainName = args[0]
    realName = args[1]
    
    if action == "add":
        #addUser(domainName, realName)
        #addDomain(domainName)
        addAliases(domainName)
    elif action == "del":
        delAliases(domainName)
        delDomain(domainName)
        #delUser(domainName)
        
    DBclose()

    print "Things to do: set passwd"


if __name__ == "__main__":
    main()