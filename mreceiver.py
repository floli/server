#!/usr/bin/python

import sys, os

import common

DB = common.DB()




def print_usage_and_exit():
    print "Usage: mreceiver {add | del | list} [email]"
    exit()
    

def get_allowed_domains(username):
    """ Returns a list of domains the local user is allowed to add addresses for. """

    sql = "SELECT domain FROM {DOMAIN_TBL} WHERE mail AND user = %s UNION SELECT alias FROM {HTTP_ALIASES_TBL} WHERE domain IN (SELECT domain FROM {DOMAIN_TBL} WHERE mail AND user = %s)"

    result, resultSet = DB.sql(sql, username, username)
    return [ dom[0] for dom in resultSet ]
    


def check_username_match(email, username):
    """ Checks if email has the correct domain. """
    try:
        user, domain = email.split("@")
    except:
        print "Something is wrong with the email you supplied: %s" % email
        exit(-1)

    if domain not in get_allowed_domains(username):
        print "You're not allowed to manage email addresses for that domain"
        exit(-1)
    
    if user in common.ADMIN_ALIASES:
        # user is a reserved administrative alias.
        print "You're not allowed to manage this alias. It is reserved for administrative purposes."
        exit(-1)


def proceed_with_listing(username):
    result, resultSet = DB.sql("SELECT virtual FROM {VIRTUAL_TBL} WHERE alias = %s" , username)
    print "Number of email addresses: " + str(result)
    print ""
    for account in resultSet:
        print account[0]
    exit()
    
  
def main():
    
    username, uid, gid = common.get_system_userdata()

    if (len(sys.argv) == 2) and (sys.argv[1] == "list"):
        proceed_with_listing(username)
    
    if not len(sys.argv) == 3:
        print_usage_and_exit()    
   
    action = sys.argv[1]
    email = sys.argv[2]
    
    check_username_match(email, username)
    
    if action == "add":
        sql = "INSERT INTO {VIRTUAL_TBL} (virtual, alias) VALUES (%s, %s)" 
        DB.sql(sql, email, username)
        print email + " added!"
        
    elif action == "del":
        sql = "DELETE FROM {VIRTUAL_TBL} WHERE virtual = %s"
        ret, resultSet = DB.sql(sql, email)
        if ret == 0:
            print "No address has been deleted!"
        else:
            print email + " deleted!"
    
    else:
        print_usage_and_exit()

if __name__ == "__main__":
    main()
