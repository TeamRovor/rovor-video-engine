#!/bin/zsh
SCRIPT_DIR="${0:A:h}"
/usr/bin/python3 "$SCRIPT_DIR/launch_evan.py"
result=$?
printf '\nPress Return to close. '
read -r reply
exit "$result"
