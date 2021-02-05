#!/bin/bash
SCRIPT_DIR=$(dirname "$0")
pkill -9 -f ray # force-kill ray sessions to make sure we start from scratch
python $SCRIPT_DIR/ml_server.py
