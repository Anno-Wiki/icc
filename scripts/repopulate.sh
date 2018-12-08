#!/bin/bash
set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
sudo echo "dropping and recreating database..."
echo "drop database icc; create database icc;" | sudo mysql icc
echo "recreating table structure..."
/home/malan/projects/icc/icc/venv/bin/flask db upgrade
$DIR/populate.sh $1
