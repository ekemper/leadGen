#!/bin/bash

# Script to kill Redis and PostgreSQL processes on the host machine
# This is useful when you want to clear conflicting processes before running Docker containers

set -e

echo "🔍 Searching for Redis and PostgreSQL processes..."

# Function to kill processes by name
kill_processes() {
    local process_name=$1
    local display_name=$2
    
    echo "🔍 Looking for $display_name processes..."
    
    # Find PIDs for the process
    pids=$(pgrep -f "$process_name" 2>/dev/null || true)
    
    if [ -z "$pids" ]; then
        echo "✅ No $display_name processes found"
        return 0
    fi
    
    echo "📋 Found $display_name processes with PIDs: $pids"
    
    # Show process details before killing
    echo "📊 Process details:"
    ps -p $pids -o pid,ppid,cmd 2>/dev/null || true
    
    # Kill processes gracefully first (SIGTERM)
    echo "🛑 Sending SIGTERM to $display_name processes..."
    for pid in $pids; do
        if kill -TERM "$pid" 2>/dev/null; then
            echo "   ✅ Sent SIGTERM to PID $pid"
        else
            echo "   ❌ Failed to send SIGTERM to PID $pid (process may already be dead)"
        fi
    done
    
    # Wait a bit for graceful shutdown
    sleep 3
    
    # Check if any processes are still running and force kill if necessary
    remaining_pids=$(pgrep -f "$process_name" 2>/dev/null || true)
    if [ -n "$remaining_pids" ]; then
        echo "⚡ Force killing remaining $display_name processes with SIGKILL..."
        for pid in $remaining_pids; do
            if kill -KILL "$pid" 2>/dev/null; then
                echo "   ✅ Force killed PID $pid"
            else
                echo "   ❌ Failed to force kill PID $pid"
            fi
        done
    fi
    
    echo "✅ $display_name cleanup completed"
}

# Function to stop systemd services if they exist
stop_systemd_service() {
    local service_name=$1
    local display_name=$2
    
    if systemctl is-active --quiet "$service_name" 2>/dev/null; then
        echo "🛑 Stopping $display_name systemd service..."
        if sudo systemctl stop "$service_name"; then
            echo "✅ Stopped $service_name service"
        else
            echo "❌ Failed to stop $service_name service"
        fi
    else
        echo "ℹ️  $service_name systemd service is not running"
    fi
}

echo "🚀 Starting cleanup of local Redis and PostgreSQL processes..."

# Stop systemd services first (if running)
echo ""
echo "📋 Checking systemd services..."
stop_systemd_service "redis-server" "Redis"
stop_systemd_service "redis" "Redis"
stop_systemd_service "postgresql" "PostgreSQL"
stop_systemd_service "postgres" "PostgreSQL"

echo ""
echo "📋 Killing individual processes..."

# Kill Redis processes
kill_processes "redis-server" "Redis"
kill_processes "redis-cli" "Redis CLI"

# Kill PostgreSQL processes
kill_processes "postgres" "PostgreSQL"
kill_processes "postgresql" "PostgreSQL"

# Kill any processes listening on the default ports
echo ""
echo "🔍 Checking for processes on default ports..."

# Check Redis port (6379)
redis_port_pid=$(lsof -ti:6379 2>/dev/null || true)
if [ -n "$redis_port_pid" ]; then
    echo "🛑 Killing process on Redis port 6379 (PID: $redis_port_pid)"
    kill -TERM "$redis_port_pid" 2>/dev/null || kill -KILL "$redis_port_pid" 2>/dev/null || true
    echo "✅ Cleared Redis port 6379"
else
    echo "✅ Redis port 6379 is free"
fi

# Check PostgreSQL port (5432)
postgres_port_pid=$(lsof -ti:5432 2>/dev/null || true)
if [ -n "$postgres_port_pid" ]; then
    echo "🛑 Killing process on PostgreSQL port 5432 (PID: $postgres_port_pid)"
    kill -TERM "$postgres_port_pid" 2>/dev/null || kill -KILL "$postgres_port_pid" 2>/dev/null || true
    echo "✅ Cleared PostgreSQL port 5432"
else
    echo "✅ PostgreSQL port 5432 is free"
fi

# Kill docker-pr processes that might be holding ports
echo ""
echo "🐳 Checking for lingering Docker port-forwarding processes..."
docker_pr_pids=$(pgrep -f "docker-pr" 2>/dev/null || true)
if [ -n "$docker_pr_pids" ]; then
    echo "🛑 Found docker-pr processes (PIDs: $docker_pr_pids)"
    for pid in $docker_pr_pids; do
        if sudo kill -KILL "$pid" 2>/dev/null; then
            echo "   ✅ Killed docker-pr PID $pid"
        else
            echo "   ❌ Failed to kill docker-pr PID $pid"
        fi
    done
else
    echo "✅ No docker-pr processes found"
fi

# Also stop any Docker containers that might be running
echo ""
echo "🐳 Stopping any remaining Docker containers..."
if command -v docker >/dev/null 2>&1; then
    # Stop all running containers
    running_containers=$(docker ps -q 2>/dev/null || true)
    if [ -n "$running_containers" ]; then
        echo "🛑 Stopping running Docker containers..."
        docker stop $running_containers 2>/dev/null || true
        docker rm $running_containers 2>/dev/null || true
        echo "✅ Stopped Docker containers"
    else
        echo "✅ No running Docker containers found"
    fi
    
    # Clean up with docker compose if available
    if [ -f "docker/docker-compose.yml" ]; then
        echo "🧹 Running docker compose down for cleanup..."
        docker compose -f docker/docker-compose.yml down 2>/dev/null || true
        echo "✅ Docker compose cleanup completed"
    fi
else
    echo "ℹ️  Docker not found, skipping container cleanup"
fi

echo ""
echo "🎉 Cleanup completed!"
echo ""
echo "📊 Final port check:"
echo "Redis port 6379: $(lsof -ti:6379 2>/dev/null && echo 'OCCUPIED' || echo 'FREE')"
echo "PostgreSQL port 5432: $(lsof -ti:5432 2>/dev/null && echo 'OCCUPIED' || echo 'FREE')"
echo ""
echo "🐳 You can now safely start your Docker containers with: make docker-up" 