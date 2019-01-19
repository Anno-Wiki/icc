#!/bin/bash

echo -n Password:
read -s password
printf '\n'

set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
sudo echo "- dropping and recreating database..."
echo "drop database icc; create database icc;" | sudo mysql icc
echo "- removing original migrations folder..."
rm -rf $DIR/../migrations
echo "- creating new migrations folder..."
$ICCVENV/bin/flask db init
echo "- recreating alembic scripts..."
$ICCVENV/bin/flask db migrate
echo "- recreating table structure..."
$ICCVENV/bin/flask db upgrade
$DIR/populate.sh $password
