#!/bin/bash
# Truncate all log files in the logs directory

: > "$(dirname "$0")/../logs/server.log"
: > "$(dirname "$0")/../logs/worker.log"
: > "$(dirname "$0")/../logs/browser.log"

echo "All logs truncated." 