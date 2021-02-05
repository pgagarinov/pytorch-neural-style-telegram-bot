#!/bin/bash
set -e
source /opt/miniconda/bin/activate
conda activate $1
SCRIPT_DIR=$(dirname "$0")
$SCRIPT_DIR/start_ml_server.sh
