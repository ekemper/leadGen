#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print banner
echo -e "${BLUE}=================================${NC}"
echo -e "${BLUE}   Flask API Test Watcher        ${NC}"
echo -e "${BLUE}=================================${NC}"
echo

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Function to display notifications (works on macOS)
notify() {
    title=$1
    message=$2
    if [ "$(uname)" == "Darwin" ]; then
        osascript -e "display notification \"$message\" with title \"$title\""
    fi
}

# Create wrapper functions for ptw callbacks
handle_pass() {
    echo -e "${GREEN}All tests passed!${NC}"
    notify "Tests Passed" "All tests completed successfully!"
}

handle_fail() {
    echo -e "${RED}Tests failed!${NC}"
    notify "Tests Failed" "Some tests failed, check the output!"
}

export -f notify
export -f handle_pass
export -f handle_fail

# Run pytest-watch with custom options
ptw \
    --onpass "bash -c handle_pass" \
    --onfail "bash -c handle_fail" \
    --runner "pytest -v --cov=. --cov-report=term-missing" \
    --ignore venv \
    --ignore .pytest_cache \
    --ignore __pycache__ \
    --ignore .coverage \
    --ignore htmlcov \
    --clear 