#!/bin/sh

[ -f /home/sync_lock ] && exit 0

cd /home
touch sync_lock

for dir in $(ls -1d */)
do
    dir=`echo "$dir" | sed s+/++`  # Get rid of the trailing slash.
    [ -f $dir/STOP_SYNC ] || rsync -av --delete root@shiva.centershock.net:/home/$dir /home/
done

echo `date` > LAST_SYNC

rm sync_lock
