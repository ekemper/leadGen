#!/bin/bash

#
# Reset and Run Concurrent Campaigns Test Script
#
# This script performs a complete reset of the application state and runs 
# the concurrent campaigns flow test to validate the system's concurrent 
# processing capabilities.
#
# Usage: ./reset_and_run_concurrent_campaigns_test.sh
#
# Exit Codes:
#   0  - Success
#   1  - Environment validation failed
#   2  - Log truncation failed
#   3  - Container restart failed
#   4  - Database truncation failed
#   5  - Redis cache clear failed
#   6  - Test execution failed
#   7  - Results validation failed
#
# Requirements:
#   - Docker and Docker Compose installed
#   - Script must be run from project root directory
#   - All containers must be running or buildable
#
# Author: AI Assistant
# Version: 1.0
#

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Container names (will be verified dynamically)
API_CONTAINER="fastapi-k8-proto-api-1"
POSTGRES_CONTAINER="fastapi-k8-proto-postgres-1"
REDIS_CONTAINER="fastapi-k8-proto-redis-1"

# Log file location
LOG_FILE="./logs/combined.log"

# Test file location
TEST_FILE="app/background_services/smoke_tests/test_concurrent_campaigns_flow.py"

# Function to print colored output
print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

# Function to print section headers
print_section() {
    echo ""
    echo -e "${PURPLE}===============================================${NC}"
    echo -e "${PURPLE} $1${NC}"
    echo -e "${PURPLE}===============================================${NC}"
}

# Cleanup function for trap
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        print_error "Script failed with exit code $exit_code"
        print_info "Check the output above for error details"
    fi
}

# Set trap for cleanup
trap cleanup EXIT

# Function to validate prerequisites
validate_prerequisites() {
    print_step "Validating prerequisites..."
    
    # Check if running from project root
    if [ ! -f "docker-compose.yml" ] || [ ! -f "Makefile" ] || [ ! -d "app" ]; then
        print_error "Script must be run from project root directory"
        print_info "Expected files: docker-compose.yml, Makefile, app/ directory"
        exit 1
    fi
    
    # Check for Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check for Docker Compose
    if ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not available"
        print_info "Please install Docker Compose (newer 'docker compose' version)"
        exit 1
    fi
    
    # Check if test file exists
    if [ ! -f "$TEST_FILE" ]; then
        print_error "Test file not found: $TEST_FILE"
        exit 1
    fi
    
    print_success "Prerequisites validated"
}

# Function to validate environment and get container names
validate_environment() {
    print_step "Validating environment and container status..."
    
    # Check if containers are running
    if ! docker ps | grep -q "fastapi-k8-proto-api"; then
        print_warning "API container not running, attempting to start services..."
        docker compose up -d
        sleep 10
    fi
    
    # Get actual container names
    API_CONTAINER=$(docker ps --format "table {{.Names}}" | grep "fastapi-k8-proto-api" | head -1)
    POSTGRES_CONTAINER=$(docker ps --format "table {{.Names}}" | grep "fastapi-k8-proto-postgres" | head -1)
    REDIS_CONTAINER=$(docker ps --format "table {{.Names}}" | grep "fastapi-k8-proto-redis" | head -1)
    
    if [ -z "$API_CONTAINER" ] || [ -z "$POSTGRES_CONTAINER" ] || [ -z "$REDIS_CONTAINER" ]; then
        print_error "Required containers not found or not running"
        print_info "Expected containers: API, PostgreSQL, Redis"
        print_info "Run 'docker compose up -d' to start services"
        exit 1
    fi
    
    print_info "Found containers:"
    print_info "  API: $API_CONTAINER"
    print_info "  PostgreSQL: $POSTGRES_CONTAINER" 
    print_info "  Redis: $REDIS_CONTAINER"
    
    # Test database connectivity
    print_step "Testing database connectivity..."
    if ! docker exec "$API_CONTAINER" python -c "from app.core.database import SessionLocal; from sqlalchemy import text; db = SessionLocal(); db.execute(text('SELECT 1')); db.close(); print('Database connection successful')" 2>/dev/null; then
        print_error "Database connection failed from API container"
        exit 1
    fi
    
    # Test Redis connectivity
    print_step "Testing Redis connectivity..."
    if ! docker exec "$API_CONTAINER" python -c "import redis; r = redis.Redis(host='redis', port=6379, db=0); r.ping(); print('Redis connection successful')" 2>/dev/null; then
        print_error "Redis connection failed from API container"
        exit 1
    fi
    
    print_success "Environment validation completed"
}

# Function to truncate log file
truncate_log_file() {
    print_step "Truncating log file: $LOG_FILE"
    
    # Create logs directory if it doesn't exist
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Truncate the log file
    if ! > "$LOG_FILE"; then
        print_error "Failed to truncate log file: $LOG_FILE"
        exit 2
    fi
    
    # Verify truncation
    if [ -s "$LOG_FILE" ]; then
        print_error "Log file is not empty after truncation"
        exit 2
    fi
    
    print_success "Log file truncated successfully"
}

# Function to restart containers
restart_containers() {
    print_step "Performing full Docker containers rebuild..."
    
    print_info "Stopping and removing all containers, networks, and volumes..."
    if ! docker compose down -v; then
        print_error "Failed to stop and remove containers"
        exit 3
    fi
    
    print_info "Building and starting containers from scratch..."
    if ! docker compose up --build -d; then
        print_error "Failed to build and start containers"
        exit 3
    fi
    
    print_step "Waiting for services to be healthy..."
    sleep 15
    
    # Wait for health checks
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker compose ps | grep -q "healthy"; then
            break
        fi
        print_info "Waiting for health checks... (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        print_warning "Health checks did not complete within expected time"
        print_info "Continuing anyway - services may still be starting"
    fi
    
    # Re-fetch container names after rebuild
    API_CONTAINER=$(docker ps --format "table {{.Names}}" | grep "fastapi-k8-proto-api" | head -1)
    POSTGRES_CONTAINER=$(docker ps --format "table {{.Names}}" | grep "fastapi-k8-proto-postgres" | head -1)
    REDIS_CONTAINER=$(docker ps --format "table {{.Names}}" | grep "fastapi-k8-proto-redis" | head -1)
    
    print_info "Updated container names after rebuild:"
    print_info "  API: $API_CONTAINER"
    print_info "  PostgreSQL: $POSTGRES_CONTAINER" 
    print_info "  Redis: $REDIS_CONTAINER"
    
    print_success "Containers rebuilt and started successfully"
}

# Function to truncate database tables
truncate_database_tables() {
    print_step "Truncating database tables..."
    
    # SQL commands to truncate tables in proper order
    local sql_commands="
        TRUNCATE TABLE jobs CASCADE;
        TRUNCATE TABLE leads CASCADE;
        TRUNCATE TABLE campaigns CASCADE;
        TRUNCATE TABLE organizations CASCADE;
        TRUNCATE TABLE users CASCADE;
    "
    
    print_info "Executing SQL commands to truncate tables..."
    
    if ! docker exec "$API_CONTAINER" python -c "
from app.core.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
try:
    db.execute(text('TRUNCATE TABLE jobs CASCADE'))
    db.execute(text('TRUNCATE TABLE leads CASCADE'))
    db.execute(text('TRUNCATE TABLE campaigns CASCADE'))
    db.execute(text('TRUNCATE TABLE organizations CASCADE'))
    db.execute(text('TRUNCATE TABLE users CASCADE'))
    db.commit()
    print('Database tables truncated successfully')
except Exception as e:
    db.rollback()
    print(f'Database truncation failed: {e}')
    raise
finally:
    db.close()
"; then
        print_error "Database table truncation failed"
        exit 4
    fi
    
    # Verify tables are empty
    print_step "Verifying table truncation..."
    if ! docker exec "$API_CONTAINER" python -c "
from app.core.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
try:
    tables = ['jobs', 'leads', 'campaigns', 'organizations', 'users']
    for table in tables:
        result = db.execute(text(f'SELECT COUNT(*) FROM {table}')).scalar()
        if result > 0:
            raise Exception(f'Table {table} is not empty: {result} rows')
        print(f'Table {table}: 0 rows (verified)')
    print('All specified tables are empty')
finally:
    db.close()
"; then
        print_error "Table truncation verification failed"
        exit 4
    fi
    
    print_success "Database tables truncated and verified"
}

# Function to clear Redis cache
clear_redis_cache() {
    print_step "Clearing Redis cache..."
    
    if ! docker exec "$API_CONTAINER" python -c "
import redis
r = redis.Redis(host='redis', port=6379, db=0)
result = r.flushall()
if result:
    print('Redis cache cleared successfully')
else:
    raise Exception('Redis FLUSHALL command failed')
"; then
        print_error "Redis cache clearing failed"
        exit 5
    fi
    
    # Verify cache is cleared
    print_step "Verifying Redis cache is empty..."
    if ! docker exec "$API_CONTAINER" python -c "
import redis
r = redis.Redis(host='redis', port=6379, db=0)
keys = r.keys('*')
if keys:
    raise Exception(f'Redis cache not empty: {len(keys)} keys found')
print('Redis cache is empty (verified)')
"; then
        print_error "Redis cache verification failed"
        exit 5
    fi
    
    print_success "Redis cache cleared and verified"
}

# Function to run the concurrent campaigns test
run_concurrent_campaigns_test() {
    print_step "Running concurrent campaigns flow test..."
    
    print_info "Starting test execution..."
    print_info "This may take several minutes to complete..."
    print_info "Test output will be displayed in real-time below:"
    
    echo ""
    echo "================== TEST OUTPUT START =================="
    
    # Run the test with real-time output piping using -t flag for pseudo-TTY
    if ! docker exec -t "$API_CONTAINER" python "$TEST_FILE"; then
        echo "=================== TEST OUTPUT END ==================="
        echo ""
        print_error "Test execution failed"
        exit 6
    fi
    
    echo "=================== TEST OUTPUT END ==================="
    echo ""
    print_success "Test execution completed successfully"
    return 0
}

# Function to validate results
validate_results() {
    print_step "Validating test results..."
    
    # Check if test created expected data
    print_step "Checking database for test data..."
    
    if ! docker exec "$API_CONTAINER" python -c "
from app.core.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
try:
    # Check campaigns
    campaign_count = db.execute(text('SELECT COUNT(*) FROM campaigns')).scalar()
    print(f'Campaigns created: {campaign_count}')
    
    # Check leads
    lead_count = db.execute(text('SELECT COUNT(*) FROM leads')).scalar()
    print(f'Leads created: {lead_count}')
    
    # Check jobs
    job_count = db.execute(text('SELECT COUNT(*) FROM jobs')).scalar()
    print(f'Jobs created: {job_count}')
    
    # Check organizations
    org_count = db.execute(text('SELECT COUNT(*) FROM organizations')).scalar()
    print(f'Organizations created: {org_count}')
    
    # Check users
    user_count = db.execute(text('SELECT COUNT(*) FROM users')).scalar()
    print(f'Users created: {user_count}')
    
    # Validate minimum expectations
    if campaign_count < 1:
        raise Exception('No campaigns were created')
    if lead_count < 1:
        raise Exception('No leads were created')
    if job_count < 1:
        raise Exception('No jobs were created')
    if user_count < 1:
        raise Exception('No users were created')
        
    print('Database validation successful')
finally:
    db.close()
"; then
        print_error "Results validation failed"
        exit 7
    fi
    
    print_success "Results validation completed"
}

# Function to display final summary
display_summary() {
    print_section "EXECUTION SUMMARY"
    
    print_success "🎉 Concurrent campaigns test completed successfully!"
    print_info "✅ Log file truncated"
    print_info "✅ Containers rebuilt and started fresh"
    print_info "✅ Database tables cleared"
    print_info "✅ Redis cache cleared"
    print_info "✅ Test executed successfully"
    print_info "✅ Results validated"
    
    echo ""
    print_info "Next steps:"
    print_info "  - Review the test output above for detailed results"
    print_info "  - Check logs/combined.log for application logs"
    print_info "  - Use 'docker exec $API_CONTAINER python -c \"from app.core.database import SessionLocal; ...\"' to query test data"
    
    echo ""
    print_success "Reset and test execution completed successfully! 🚀"
}

# Main execution function
main() {
    print_section "RESET AND RUN CONCURRENT CAMPAIGNS TEST"
    
    print_info "This script will:"
    print_info "  1. Validate environment and prerequisites"
    print_info "  2. Truncate the combined.log file"
    print_info "  3. Full rebuild Docker containers (down -v && up --build)"
    print_info "  4. Truncate database tables (jobs, leads, campaigns, organizations, users)"
    print_info "  5. Clear Redis cache"
    print_info "  6. Run the concurrent campaigns flow test"
    print_info "  7. Validate results"
    
    echo ""
    print_warning "⚠️  WARNING: This will DELETE ALL DATA in the specified database tables!"
    print_warning "⚠️  Make sure you're running this in a development environment!"
    
    echo ""
    read -p "Do you want to continue? (y/N): " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Operation cancelled by user"
        exit 0
    fi
    
    # Execute all phases
    print_section "PHASE 1: ENVIRONMENT VALIDATION"
    validate_prerequisites
    validate_environment
    
    print_section "PHASE 2: LOG FILE MANAGEMENT"
    truncate_log_file
    
    print_section "PHASE 3: CONTAINER REBUILD"
    restart_containers
    
    print_section "PHASE 4: DATABASE TABLE TRUNCATION"
    truncate_database_tables
    
    print_section "PHASE 5: REDIS CACHE CLEARING"
    clear_redis_cache
    
    print_section "PHASE 6: TEST EXECUTION"
    run_concurrent_campaigns_test
    
    print_section "PHASE 7: RESULTS VALIDATION"
    validate_results
    
    display_summary
}

# Execute main function
main "$@" 