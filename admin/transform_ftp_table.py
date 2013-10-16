import csv
from subprocess import Popen, PIPE
import csv

accfile = open("ftp.csv", "r")
outfile = open("ftp-out.csv", "w")

out = csv.writer(outfile, delimiter=",", quotechar='"', quoting=csv.QUOTE_NONNUMERIC)

for acc in csv.reader(accfile, delimiter=",", quotechar='"'):
    # Hash and replace password
    proc = Popen( ["/usr/sbin/ftpasswd", "--hash", "--stdin"], stdout=PIPE, stdin=PIPE)
    output, err = proc.communicate(acc[2])
    if proc.returncode != 0:
        print "FEHLER"
    pwd = output[10:].strip()
    acc[2] = pwd

    out.writerow(acc)
    
