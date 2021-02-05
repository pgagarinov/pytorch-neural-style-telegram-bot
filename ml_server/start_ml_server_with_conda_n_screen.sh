#!/bin/bash
set -e
#
SCRIPT_DIR=$(dirname "$0")
rm -f $SCRIPT_DIR/screenlog.0
screen -X -S style_ml_server kill || true
screen -S style_ml_server -L -d -m -Logfile $SCRIPT_DIR/screenlog.0 $SCRIPT_DIR/start_ml_server_with_conda.sh $1
sleep 1
screen -ls
sleep 1
sync
watch cat $SCRIPT_DIR/screenlog.0

