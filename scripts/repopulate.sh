#!/bin/bash
if [[ $# -eq 0 ]] ; then
    echo "- need password for all default users."
    exit 127
fi
set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
sudo echo "- dropping and recreating database..."
echo "drop database icc; create database icc;" | sudo mysql icc
echo "- recreating table structure..."
$DIR/../venv/bin/flask db upgrade
$DIR/populate.sh $1
