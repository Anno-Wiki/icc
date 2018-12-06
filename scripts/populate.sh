#!/bin/bash
set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
echo "populating books, authors, and enum tables..."
sudo mysql icc < /home/malan/projects/icc/data/run.sql
echo "creating default users..."
$DIR/../createdefaultusers.py -p "send9856"
echo "populating lines for Heart of Darkness by Joseph Conrad..."
cat /home/malan/projects/icc/data/hod/HeartofDarknessbyJosephConrad.icc | $DIR/../insertlines.py -b 1
echo "populating lines for War and Peace by Leo Tolstoy"
cat /home/malan/projects/icc/data/wap/WarandPeacebygrafLeoTolstoy.icc | $DIR/../insertlines.py -b 2
echo "adding annotations for War and Peace by Constance Garnett..."
cat /home/malan/projects/icc/data/wap/WarandPeacebygrafLeoTolstoy.anno | $DIR/../insertannotations.py -b 2 -a "constance-garnett"
