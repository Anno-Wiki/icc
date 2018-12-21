#!/bin/bash
if [[ $# -eq 0 ]] ; then
    echo "- need password for all default users."
    exit 127
fi

set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

echo "- populating enum tables..."
sudo mysql icc < $DIR/sql/connection_enums.sql
sudo mysql icc < $DIR/sql/flags.sql
sudo mysql icc < $DIR/sql/line_enums.sql
sudo mysql icc < $DIR/sql/notification_enums.sql
sudo mysql icc < $DIR/sql/reputation_enums.sql
sudo mysql icc < $DIR/sql/rights.sql

echo "- creating default users..."
$DIR/../insertusers.py -p $1 -c $DIR/users.yml

# The default users have to be created first because all the tags that use wikis
# require the default (Community) to be created first.
echo "- populating tags..."
$DIR/../inserttags.py -c $DIR/tags.yml

echo "- populating lines for Heart of Darkness by Joseph Conrad..."
cat $DIR/../texts/hod/HeartofDarknessbyJosephConrad.icc | \
    $DIR/../insertlines.py -i -c $DIR/../texts/hod/hod.yml

echo "- populating lines for War and Peace by Leo Tolstoy"
cat $DIR/../texts/wap/WarandPeacebygrafLeoTolstoy.icc | \
    $DIR/../insertlines.py -i -c $DIR/../texts/wap/wap.yml

echo "- adding annotations for War and Peace by Constance Garnett..."
cat $DIR/../texts/wap/WarandPeacebygrafLeoTolstoy.ano | \
    $DIR/../insertannotations.py -t "War and Peace" -e 1 -a "constance-garnett"
