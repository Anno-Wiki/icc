#!/bin/bash

echo -n Default User Password:
read -s password
printf '\n'

set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
ROOT=$DIR/../..
DATA=$DIR/..
LIBRARY=$DATA/library
PYTHON=$ICCVENV/bin/python

echo "- populating enum tables..."
$PYTHON $ROOT/inserts/insertenums.py -c $DATA/enums.yml

echo "- creating default users..."
$PYTHON $ROOT/inserts/insertusers.py -p $password -c $DATA/users.yml

# The default users have to be created first because all the tags that use wikis
# require the default (Community) to be created first.
echo "- populating tags..."
$PYTHON $ROOT/inserts/inserttags.py -c $DATA/tags.yml

#######################################

echo "- populating lines for Heart of Darkness by Joseph Conrad..."
$PYTHON $ROOT/inserts/insertlines.py $LIBRARY/conrad_joseph/hod

echo "- populating lines for War and Peace by Leo Tolstoy"
$PYTHON $ROOT/inserts/insertlines.py $LIBRARY/tolstoy_leo/wap

echo "- populating annotations for War and Peace by Leo Tolstoy"
$PYTHON $ROOT/inserts/insertannotations.py \
    -i $LIBRARY/tolstoy_leo/wap/initial_annotations.json\
    -a 'constance-garnett' -t 'War and Peace' -e 1
$PYTHON $ROOT/annotations.py -i $LIBRARY/tolstoy_leo/wap/annotations.json

echo "- populating lines for War and Peace by Leo Tolstoy"
$PYTHON $ROOT/inserts/insertlines.py $LIBRARY/bible/kjv/kjbo

echo "- populating lines for Shakespeare's Pericles"
$PYTHON $ROOT/inserts/insertlines.py $LIBRARY/shakespeare_william/mit/pericles

echo "- populating lines for Shakespeare's Sonnets"
$PYTHON $ROOT/inserts/insertlines.py $LIBRARY/shakespeare_william/mit/sonnets

echo "- populating lines for Shakespeare's Taming of the Shrew"
$PYTHON $ROOT/inserts/insertlines.py $LIBRARY/shakespeare_william/mit/taming_shrew

echo "- populating lines for shakespeare"
for file in $LIBRARY/shakespeare_william/mit/processed/*; do
    echo "- populationg lines for $file"
    $PYTHON $ROOT/inserts/insertlines.py $file;
done
