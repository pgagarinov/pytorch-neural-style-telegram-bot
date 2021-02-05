# Copyright Peter Gagarinov.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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

