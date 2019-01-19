#!/bin/bash

password=$1

if [[ -z ${password+x} ]]; then
    echo -n Password:
    read -s password
    printf '\n'
fi

set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

echo "- populating enum tables..."
$ICCVENV/bin/python $DIR/../insertenums.py -c $DIR/../data/enums.yml

echo "- creating default users..."
$ICCVENV/bin/python $DIR/../insertusers.py -p $password -c $DIR/../data/users.yml

# The default users have to be created first because all the tags that use wikis
# require the default (Community) to be created first.
echo "- populating tags..."
$ICCVENV/bin/python $DIR/../inserttags.py -c $DIR/../data/tags.yml

echo "- populating lines for Heart of Darkness by Joseph Conrad..."
cat $DIR/../data/texts/hod/hod.lines.json | \
    $ICCVENV/bin/python $DIR/../insertlines.py -i -c $DIR/../data/texts/hod/hod.yml

echo "- populating lines for War and Peace by Leo Tolstoy"
cat $DIR/../data/texts/wap/wap.lines.json | \
    $ICCVENV/bin/python $DIR/../insertlines.py -i -c $DIR/../data/texts/wap/wap.yml

echo "- adding annotations for War and Peace by Constance Garnett..."
cat $DIR/../data/texts/wap/wap.ano.json | \
    $ICCVENV/bin/python $DIR/../insertannotations.py -t "War and Peace" -e 1 -a "constance-garnett"
