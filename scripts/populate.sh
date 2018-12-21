#!/bin/bash
if [[ $# -eq 0 ]] ; then
    echo "- need password for all default users."
    exit 127
fi

set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

echo "- populating enum tables..."
$DIR/../insertenums.py -c $DIR/../data/enums.yml

echo "- creating default users..."
$DIR/../insertusers.py -p $1 -c $DIR/../data/users.yml

# The default users have to be created first because all the tags that use wikis
# require the default (Community) to be created first.
echo "- populating tags..."
$DIR/../inserttags.py -c $DIR/../data/tags.yml

echo "- populating lines for Heart of Darkness by Joseph Conrad..."
cat $DIR/../data/texts/hod/hod.lines.json | \
    $DIR/../insertlines.py -i -c $DIR/../data/texts/hod/hod.yml

echo "- populating lines for War and Peace by Leo Tolstoy"
cat $DIR/../data/texts/wap/wap.lines.json | \
    $DIR/../insertlines.py -i -c $DIR/../data/texts/wap/wap.yml

echo "- adding annotations for War and Peace by Constance Garnett..."
cat $DIR/../data/texts/wap/wap.ano.json | \
    $DIR/../insertannotations.py -t "War and Peace" -e 1 -a "constance-garnett"
