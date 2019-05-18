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
$PYTHON $ROOT/inserts/insertlines.py -c $DATA/texts/hod/meta.yml \
    -i $DATA/texts/conrad_joseph/hod/lines.json

echo "- populating lines for War and Peace by Leo Tolstoy"
$PYTHON $ROOT/inserts/insertlines.py -c $DATA/texts/wap/meta.yml \
    -i $DATA/texts/tolstoy_leowap/lines.json

echo "- populating annotations for War and Peace by Leo Tolstoy"
$PYTHON $ROOT/annotations.py -i $DATA/texts/tolstoy_leo/wap/annotations.json

echo "- populating lines for The King James Bible"
$PYTHON $ROOT/inserts/insertlines.py -c $DATA/texts/bible/meta.yml \
    -i $DATA/texts/bible/lines.json

echo "- populating lines for Shakespare's Sonnets"
$PYTHON $ROOT/inserts/insertlines.py \
    -c $data/texts/shakespeare_william/sonnets/meta.yml \
    -i $DATA/texts/shakespeare_william/sonnets/lines.json

echo "- populating lines for Shakespare's Hamlet"
$PYTHON $ROOT/inserts/insertlines.py \
    -c $data/texts/shakespeare_william/hamlet/meta.yml \
    -i $DATA/texts/shakespeare_william/hamlet/lines.json

echo "- populating lines for Shakespare's Macbeth"
$PYTHON $ROOT/inserts/insertlines.py \
    -c $data/texts/shakespeare_william/macbeth/meta.yml \
    -i $DATA/texts/shakespeare_william/macbeth/lines.json
