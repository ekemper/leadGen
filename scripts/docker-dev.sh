#!/bin/bash
set -e

# Docker development helper script

# Detect docker compose command
if command -v docker-compose &> /dev/null; then
  DC="docker-compose"
elif docker compose version &> /dev/null; then
  DC="docker compose"
else
  echo "Error: Neither 'docker-compose' nor 'docker compose' is available. Please install Docker Compose."
  exit 1
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if containers are running
check_containers() {
    if ! docker ps | grep -q "leadgen-api"; then
        print_error "API container is not running. Please start with 'docker compose up -d'"
        exit 1
    fi
}

case "$1" in
  start)
    echo "Starting Docker services..."
    $DC up -d
    echo "Services started. API: http://localhost:8000, Flower: http://localhost:5555"
    ;;
  
  stop)
    echo "Stopping Docker services..."
    $DC down
    ;;
  
  restart)
    echo "Restarting Docker services..."
    $DC restart
    ;;
  
  logs)
    $DC logs -f ${2:-}
    ;;
  
  build)
    echo "Building Docker images..."
    $DC build ${2:-}
    ;;
  
  shell)
    check_containers
    service=${2:-api}
    $DC exec $service /bin/bash
    ;;
  
  psql)
    check_containers
    $DC exec postgres psql -U postgres -d lead_gen
    ;;
  
  redis)
    check_containers
    $DC exec redis redis-cli
    ;;
  
  test)
    echo "Running tests in Docker..."
    $DC run --rm api pytest tests/ -v
    ;;
  
  migrate)
    check_containers
    $DC exec api alembic upgrade head
    ;;
  
  makemigration)
    check_containers
    $DC exec api alembic revision --autogenerate -m "${2:-Auto migration}"
    ;;
  
  clean)
    echo "Cleaning up Docker resources..."
    $DC down -v
    docker system prune -f
    ;;
  
  help)
    echo "Development Helper Script"
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  start              Start development environment"
    echo "  stop               Stop development environment"
    echo "  restart            Restart development environment"
    echo "  logs [service]     Show logs (default: api)"
    echo "  shell [service]    Open shell in container (default: api)"
    echo "  psql               Connect to PostgreSQL"
    echo "  redis              Connect to Redis CLI"
    echo "  test               Run tests"
    echo "  migrate            Run database migrations"
    echo "  makemigration [msg] Create new migration"
    echo "  help               Show this help"
    ;;
  
  *)
    echo "Usage: $0 {start|stop|restart|logs|build|shell|psql|redis|test|migrate|makemigration|clean|help} [service]"
    exit 1
    ;;
esac 