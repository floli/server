import MySQLdb
import configparser, os, sys

DOMAIN_TBL = "domains"
VIRTUAL_TBL = "virtual_aliases"
MAILBOX_TBL = "mailboxes"
FTP_TBL = "ftp" 

# Table that contains further HTTP aliases for a domain
HTTP_ALIASES_TBL = "http_aliases"

# Reserved aliases that get forwarded to root
ADMIN_ALIASES = ["hostmaster", "postmaster", "newsmaster", "mailmaster", "abuse"]


class DB:
    def __init__(self):
        config = configparser.SafeConfigParser()
        config.read(os.path.join(os.path.dirname(sys.argv[0]), "configuration"))
        DB_USER = config.get("CREDENTIALS", "DB_USER")
        DB_PASSWD = config.get("CREDENTIALS", "DB_PASSWD")
        DATABASE = config.get("CREDENTIALS", "DATABASE")
        self.conn = MySQLdb.connect(host="localhost", user=DB_USER, passwd=DB_PASSWD, db=DATABASE)

    def replDBinfo(self, s):
        return s.format(DOMAIN_TBL=DOMAIN_TBL,
                        VIRTUAL_TBL=VIRTUAL_TBL, HTTP_ALIASES_TBL=HTTP_ALIASES_TBL,
                        MAILBOX_TBL=MAILBOX_TBL, FTP_TBL=FTP_TBL)

        
    def sql(self, sql, *paras):
        sql = self.replDBinfo(sql)
        try:
            cursor = self.conn.cursor()
            if len(paras):
                ret = cursor.execute(sql, paras)
            else:
                ret = cursor.execute(sql)
            resultSet = cursor.fetchall()
            cursor.close()
            self.conn.commit() # A transaction is implicitly started, so we need to finish it.
            return ret, resultSet        
        
        except MySQLdb.IntegrityError as error:
            print("A database integrity error has occured. Maybe you try to add an already existing entry?")
            print("The exception message is:", error[1])
            sys.exit(-1)
        except Exception as error:
            print("Some unhandled error has occured. Please contact root and describe what you were trying to do and add the following message.")
            print(error)
            sys.exit(-1)


                
def get_system_userdata():
    """ Returns a tuple consisting of username, UID and GID of the user that called sudo."""
    username = os.environ['SUDO_USER']
    uid = os.environ['SUDO_UID']
    gid = os.environ['SUDO_GID']
    return username, uid, gid


