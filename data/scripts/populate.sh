#!/bin/bash

password=$1

if [[ -z ${password+x} ]]; then
    echo -n Default User Password:
    read -s password
    printf '\n'
fi

set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
ROOT=$DIR/../..
DATA=$DIR/..
PYTHON=$ICCVENV/bin/python

echo "- populating enum tables..."
$PYTHON $ROOT/inserts/insertenums.py -c $DATA/enums.yml

echo "- creating default users..."
$PYTHON $ROOT/inserts/insertusers.py -p $password -c $DATA/users.yml

# The default users have to be created first because all the tags that use wikis
# require the default (Community) to be created first.
echo "- populating tags..."
$PYTHON $ROOT/inserts/inserttags.py -c $DATA/tags.yml

echo "- populating lines for Heart of Darkness by Joseph Conrad..."
$PYTHON $ROOT/inserts/insertlines.py -f -c $DATA/texts/hod/meta.yml \
    -i $DATA/texts/hod/lines.json

echo "- populating lines for War and Peace by Leo Tolstoy"
$PYTHON $ROOT/inserts/insertlines.py -f -c $DATA/texts/wap/meta.yml \
    -i $DATA/texts/wap/lines.json

echo "- populating annotations for War and Peace by Leo Tolstoy"
$PYTHON $ROOT/annotations.py -i $DATA/texts/wap/annotations.json

echo "- populating lines for The King James Bible"
$PYTHON $ROOT/inserts/insertlines.py -f -c $DATA/texts/bible/meta.yml \
    -i $DATA/texts/bible/lines.json
