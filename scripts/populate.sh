#!/bin/bash
if [[ $# -eq 0 ]] ; then
    echo "Need password for all default users."
    exit 127
fi

set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

echo "populating enum tables..."
sudo mysql icc < $DIR/sql/connection_enums.sql
sudo mysql icc < $DIR/sql/line_enums.sql
sudo mysql icc < $DIR/sql/notification_enums.sql
sudo mysql icc < $DIR/sql/reputation_enums.sql
sudo mysql icc < $DIR/sql/rights.sql

echo "populating tags..."
sudo mysql icc < $DIR/sql/tags.sql
echo "populating texts..."
sudo mysql icc < $DIR/sql/texts.sql
echo "populating writers..."
sudo mysql icc < $DIR/sql/writers.sql

echo "creating default users..."
$DIR/../createdefaultusers.py -p $1

echo "populating lines for Heart of Darkness by Joseph Conrad..."
cat $DIR/../../data/hod/HeartofDarknessbyJosephConrad.icc | \
    $DIR/../insertlines.py -t 1

echo "populating lines for War and Peace by Leo Tolstoy"
cat $DIR/../../data/wap/WarandPeacebygrafLeoTolstoy.icc | \
    $DIR/../insertlines.py -t 2 -w "Constance Garnett(Translator)"

echo "adding annotations for War and Peace by Constance Garnett..."
cat $DIR/../../data/wap/WarandPeacebygrafLeoTolstoy.anno | \
    $DIR/../insertannotations.py -e 2 -a "constance-garnett"
