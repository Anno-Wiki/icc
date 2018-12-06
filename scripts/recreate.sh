#!/bin/bash
set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
sudo echo "dropping and recreating database..."
echo "drop database icc; create database icc;" | sudo mysql icc
echo "removing original migrations folder..."
rm -rf ../migrations
echo "creating new migrations folder..."
/home/malan/projects/icc/icc/venv/bin/flask db init
echo "recreating alembic scripts..."
/home/malan/projects/icc/icc/venv/bin/flask db migrate
echo "recreating table structure..."
/home/malan/projects/icc/icc/venv/bin/flask db upgrade
$DIR/populate.sh
