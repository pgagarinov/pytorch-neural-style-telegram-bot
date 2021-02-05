#!/bin/bash
set -e
#
rm -f ./screenlog.0
screen -S style_ml_server -X quit || true
screen -S style_ml_server -L -d -m ./start_ml_server_with_conda.sh $1
sleep 1
screen -ls
sleep 1
sync
watch cat ./screenlog.0

