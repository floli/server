#!/bin/sh

[ -f /home/sync_lock ] && exit 0

cd /home
touch sync_lock

for dir in $(ls -1 .)
do
    [ -f $dir/STOP_SYNC ] || echo "rsync -av --delete root@serpent.de:/home/$dir /home/"
done

rm sync_lock