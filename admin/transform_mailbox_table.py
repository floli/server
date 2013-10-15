import csv

import csv

accfile = open("accounts.csv", "r")
outfile = open("accounts-out.csv", "w")

out = csv.writer(outfile, delimiter=",", quotechar='"')

for acc in csv.reader(accfile, delimiter=",", quotechar='"'):
    # Sets home to maildir location
    acc[3] = acc[4] 

    # Hash and replace password
    acc[2] = check_output( ["/usr/bin/doveadm","pw","-s", "SSHA512", "-p", acc[2]] )

    out.writerow(acc)
    
