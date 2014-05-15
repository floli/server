Projekt Free Server
===================

Die Idee zu diesem Projekt entstand im Frühjahr 2003. Wir wollten eine Server/Webhostingumgebung schaffen in der der einzelne Benutzer großmögliche Freiheiten hat. Die Administration der Umgebung erfolgt nicht wie üblich über ein Webinterface sondern über SSH. So können komplexere Aufgaben über Scripte automatisiert werden. Dies setzt natürlich Grundkentnisse in Linux/Unix vorraus.

Ganz kurz die Fakten:

* Zu einem Account gehört jeweils ein SSH Shell Zugang. Es können aber prinzipiell beliebig viele Domains auf einen Account geschaltet werden.
* FTP Zugänge werden über SSH angelegt. Sie können jeweils auf ein Verzeichniss begrenzt werden. Es können beliebig viele FTP Zugänge angelegt werden.
* Die Mailzustellung wird über eine Filterdatei im Home-Verzeichniss des Benutzers gesteuert und so in verschiedene Maildirs geleitet. In der Filterdatei kann z.B. auf Spam überprüft oder an andere Adressen weitergeleitet werden.
* POP3/IMAP Zugänge werden über SSH angelegt und zeigen jeweils auf ein Maildir. Jeder POP3/IMAP Zugang ist auch automatisch ein SMTP Relay Zugang. TLS-Verschlüsselung wird angeboten.
* Logdateien des HTTP-Servers werden generiert. Sie können über eigene Software oder mittels AWStats vom System ausgewertet werden.
* Es stehen 4 GB Speicherplatz zur Verfügung. Es kann auf Anfrage mehr Speicherplatz gewährt werden.
* Zu jedem Account gehört ein MySQL Benutzer. Dieser kann selbstständig neue Datenbanken anlegen. Zur Administration ist phpMyAdmin installiert.
* Traffic ist solange unbegrenzt, solange der Inklusivtraffic ausreicht. Bisher war das noch nie annähernd ein Problem.
* Als Web-Scriptsprache steht momentan PHP über mod_php zur Verfügung. Als Skriptsprachen auf den Server zusätzlich Python, Ruby, Perl, Bash und sh.
* Es können beliebig eigene Programme auf den Server installiert werden und unter Vorbehalt und mit Einschränkungen auch Server laufen gelassen werden.

Vorraussetzungen, die Du mitbringen solltest:

* Etwas Wissen über Linux/Unix Systeme oder die Bereitschaft sich etwas einzuarbeiten. Bei Fragen wird Dir gerne hier im Forum geholfen.
* Eine Second-Level-Domain (also einfach eine ganz normale Domain) bei einem Provider, bei dem Du die A- bzw. MX-Records ändern kannst. (MX nur wenn auch E-Mail über den Server laufen soll).
* Sonderwünsche werden natürlich immer probiert umzusetzen. Einfach Anfragen!

Bei Fragen oder Interesse einfach an root@centershock.net schreiben.

Hardware
--------
Der Server ist ein virtueller Server.

System Benutzer
--------------
Jedes Mitglied bekommt einen System Account in der Form erster Buchstabe vom Vornamen + Nachname. Dem Benutzer zugeordnet ist das Heimatverzeichniss /home/benutzername/ im folgenden auch mit ~ abgekürzt. In diesem Verzeichnis befinden sich u.a. das Verzeichnis Mail/ und pro Domäne ein Verzeichnis domain.tld/. Diese wiederum haben die Unterzeichnisse pub/, log/ und tmp/. Das Password kann durch die Eingabe von passwd auf der Kommandozeile geändert werden.

Cron
----
Der Cron Daemon ermöglicht es, zeitgesteuert Aufgaben auszuführen.

Datenbank
---------
Als Datenbank ist MySQL installiert. Auch phpMyAdmin ist unter [https://centershock.net/admin/database/](https://centershock.net/admin/database/) verfügbar. Das Passwort kann über die entsprechende Option in phpMyAdmin geändert werden

FTP
---
Jeder Benutzer kann beliebig viele FTP-Accounts per SSH anlegen. Dabei lässt sich der FTP-Zugang auf ein bestimmtes Verzeichnis limitieren. Ein neuer Zugang wird wie folgt angelegt:

`account ftp add -l LOGIN -p PASSWORD -d DIR`

Für Zugriff auf das aktuelle Verzeichnis muss für DIR einfach "." angegeben werden. LOGIN hat die Form benutzer@domain.tld wobei domain.tld eine dem Benutzer zugeordnete Domäne seien muss. Gelöscht werden können FTP-Zugänge mit:

`account ftp del LOGIN`

Alle angelegten Zugänge werden aufgelistet mit:

`account ftp list`

E-Mail
-----
### Freischalten von E-Mail Adressen
Damit E-Mails vom Server überhaupt angenommen werde, müssen diese Adressen erst freigeschaltet werden:

`mreceiver add user@domain.tld`

Sie kommen wieder gelöscht werden mit:

`mreceiver del user@domain.tld`

Eine Liste alle freigeschalteten Adressen kann ausgegeben werden mit:

`mreiceiver list`

### Konfiguration des Mailfilters
Nachdem eine E-Mail vom SMTP-Server angenommen wurde, wird sie an das Programm maildrop weitergeben. Dies wird über eine Datei .mailfilter in Homeverzeichnis des Benutzers gesteuert. Im Urzustand sieht diese folgendermaßen aus:
```
MDIR ="$HOME/Mail"

/^X-Original-To: (.*)$/
ADR = tolower($MATCH1)

# Uncomment this if you want to extract user and domain from the address.
# /^X-Original-To: (.*)@(.*)$/
# USERPART = tolower($MATCH1)
# DOMAINPART = tolower($MATCH2)

to "$MDIR/$LOGNAME"
```
Die erste Zeile definiert die Variable MDIR, sie dient nur zur Schreiberleichterung. In den beiden darauffolgenden Spachen wird die Empfängeradresse aus dem X-Original-To-Header extrahiert und sichergestellt, dass sie immer in Kleinbuchstaben vorliegt.

Jedem Systembenutzer ist automatisch gleichnamige eine Mail Adresse zugeordnet. Es ist wichtig, dass diese auch tatsächlich gelesen wird. Will man über den Server keine E-Mails empfangen können sie mit `to "! user@host.tld` an eine externe Adresse weitergeleitet werden.

Die letzte Zeile stellt alle E-Mails an eine Maildir zu, welches den Namen des Systembenutzers entspricht

**WICHTIG:** Die Maildirs müssen zuvor mit maildirmake angelegt werden (siehe unten).

Hat man den Verdacht, dass Mails nicht zugestellt werden, kann man mit `/usr/sbin/postqueue -p` einen Blick in die Warteschlange werfen. Dort finden sich auch die Fehlerausgaben von Maildrop, wenn die .mailfilter fehlerhaft ist.

### Anlegen von Maildirs
Damit der POP3/IMAP Server auf die E-Mails zugreifen kann, müssen diese in einen sog. Maildir untergebracht werden. Diese werdem mit `maildirmake DIR` angelegt. Es empfiehlt sich alle Maildirs unterhalb von ~/Mail anzulegen.

### Anlegen von POP3/IMAP Zugängen
Wichtig ist zu beachten, dass der verwendete IMAP/POP3 Server courier nur auf Maildirs zugreifen kann. Verwaltet werden Accounts mit genauso wie FTP Zugänge mit dem Programm account. z.B.

`account mailbox add -l LOGIN -p PASSWORD -d MAILDIR`

PHP
---
Es ist PHP 5 als mod_php installiert. Die genaue Konfiguration findet sich mit phpinfo().

Subdomains
----------
Um eine Subdomain einer existierenden Domäne auf das Unterverzeichnis subdir zu schalten, muss in der Datei ~/example.com/pub/.htaccess folgendes eingetragen werden:
```
RewriteEngine On
RewriteCond %{HTTP_HOST} ^.*sub\.example\.com$
RewriteCond %{REQUEST_URI} !^/subdir/
RewriteRule ^(.*)$ /subdir/$1
```

Impressum
---------
Dieser Service ist rein privater Natur und es werden keinerlei Gewinne erzielt. Der Server wird betrieben von:
```
Florian Lindner
Höhenweg 17
65510 Idstein
Tel: 0175 8204160
```
