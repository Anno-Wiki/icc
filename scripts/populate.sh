#!/bin/bash

password=$1

if [[ -z ${password+x} ]]; then
    echo -n Default User Password:
    read -s password
    printf '\n'
fi

set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

echo "- populating enum tables..."
$ICCVENV/bin/python $DIR/../inserts/insertenums.py -c $DIR/../data/enums.yml

echo "- creating default users..."
$ICCVENV/bin/python $DIR/../inserts/insertusers.py -p $password \
    -c $DIR/../data/users.yml

# The default users have to be created first because all the tags that use wikis
# require the default (Community) to be created first.
echo "- populating tags..."
$ICCVENV/bin/python $DIR/../inserts/inserttags.py \
    -c $DIR/../data/tags.yml

echo "- populating lines for Heart of Darkness by Joseph Conrad..."
cat $DIR/../data/texts/hod/lines.json | \
    $ICCVENV/bin/python $DIR/../inserts/insertlines.py -i \
    -c $DIR/../data/texts/hod/meta.yml

echo "- populating lines for War and Peace by Leo Tolstoy"
cat $DIR/../data/texts/wap/lines.json | \
    $ICCVENV/bin/python $DIR/../inserts/insertlines.py -i \
    -c $DIR/../data/texts/wap/meta.yml

echo "- adding annotations for War and Peace by Constance Garnett..."
cat $DIR/../data/texts/wap/annotations.json | \
    $ICCVENV/bin/python $DIR/../inserts/insertannotations.py\
    -t "War and Peace" -e 1 -a "Constance Garnett"
