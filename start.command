#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

python3 start.py
status=$?

echo
read -r -p "Press Enter to close..." _
exit "$status"
