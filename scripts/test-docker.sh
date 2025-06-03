#!/bin/bash
set -e

echo "Running tests in Docker..."

docker compose -f docker-compose.test.yml up --build --abort-on-container-exit

echo "Test coverage report available in htmlcov/index.html"

docker compose -f docker-compose.test.yml down -v 