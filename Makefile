.PHONY: help docker-start docker-stop docker-logs docker-build docker-test docker-clean

help:
	@echo "Available commands:"
	@echo "  make docker-start    - Start all Docker services"
	@echo "  make docker-stop     - Stop all Docker services"
	@echo "  make docker-logs     - View Docker logs"
	@echo "  make docker-build    - Build Docker images"
	@echo "  make docker-test     - Run tests in Docker"
	@echo "  make docker-clean    - Clean up Docker resources"

docker-start:
	./scripts/docker-dev.sh start

docker-stop:
	./scripts/docker-dev.sh stop

docker-logs:
	./scripts/docker-dev.sh logs

docker-build:
	./scripts/docker-dev.sh build

docker-test:
	./scripts/docker-dev.sh test

docker-clean:
	./scripts/docker-dev.sh clean 