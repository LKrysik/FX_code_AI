#!/bin/bash
set -e

# Blue-Green Deployment Script for FX Trading System
# Zero-downtime deployment with automatic health checks and rollback
# Usage: ./deploy.sh [--skip-build] [--no-rollback]

# Configuration
BLUE_PORT=8080
GREEN_PORT=8081
BLUE_FRONTEND_PORT=3000
GREEN_FRONTEND_PORT=3002
HEALTH_CHECK_URL="http://localhost"
MAX_HEALTH_RETRIES=10
HEALTH_CHECK_INTERVAL=5
SMOKE_TEST_DURATION=30  # seconds to monitor after switch
NGINX_CONFIG="/etc/nginx/conf.d/trading.conf"
LOG_FILE="./logs/deployment-$(date +%Y%m%d-%H%M%S).log"

# Command line options
SKIP_BUILD=false
NO_ROLLBACK=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --no-rollback)
            NO_ROLLBACK=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--skip-build] [--no-rollback]"
            exit 1
            ;;
    esac
done

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✓${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ✗${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠${NC} $1" | tee -a "$LOG_FILE"
}

# Create logs directory
mkdir -p logs

# Function to get currently active environment
get_active_env() {
    if curl -sf ${HEALTH_CHECK_URL}:${BLUE_PORT}/health > /dev/null 2>&1; then
        echo "blue"
    elif curl -sf ${HEALTH_CHECK_URL}:${GREEN_PORT}/health > /dev/null 2>&1; then
        echo "green"
    else
        echo "none"
    fi
}

# Function to wait for health check
wait_for_health() {
    local port=$1
    local service_name=$2
    local retries=0

    log "Waiting for $service_name health check on port $port..."

    while [ $retries -lt $MAX_HEALTH_RETRIES ]; do
        if curl -sf ${HEALTH_CHECK_URL}:${port}/health/ready > /dev/null 2>&1; then
            log_success "Health check passed for $service_name on port $port"
            return 0
        fi
        log "Health check attempt $((retries + 1))/$MAX_HEALTH_RETRIES for $service_name..."
        sleep $HEALTH_CHECK_INTERVAL
        retries=$((retries + 1))
    done

    log_error "Health check failed for $service_name after $MAX_HEALTH_RETRIES attempts"
    return 1
}

# Function to run smoke tests
run_smoke_tests() {
    local port=$1
    local env=$2

    log "Running smoke tests on $env environment (port $port)..."

    # Test 1: Basic health endpoint
    if ! curl -sf ${HEALTH_CHECK_URL}:${port}/health > /dev/null 2>&1; then
        log_error "Smoke test failed: Health endpoint not responding"
        return 1
    fi

    # Test 2: Ready endpoint (includes DB connection)
    if ! curl -sf ${HEALTH_CHECK_URL}:${port}/health/ready > /dev/null 2>&1; then
        log_error "Smoke test failed: Ready endpoint failed (database may be down)"
        return 1
    fi

    # Test 3: WebSocket endpoint
    if ! curl -sf ${HEALTH_CHECK_URL}:${port}/ws > /dev/null 2>&1; then
        log_warning "WebSocket endpoint check inconclusive (expected for curl)"
    fi

    # Test 4: Monitor for stability
    log "Monitoring $env environment for $SMOKE_TEST_DURATION seconds..."
    local monitor_start=$(date +%s)
    local failures=0

    while [ $(($(date +%s) - monitor_start)) -lt $SMOKE_TEST_DURATION ]; do
        if ! curl -sf ${HEALTH_CHECK_URL}:${port}/health > /dev/null 2>&1; then
            failures=$((failures + 1))
            if [ $failures -gt 3 ]; then
                log_error "Smoke test failed: Too many health check failures during monitoring"
                return 1
            fi
        fi
        sleep 5
    done

    log_success "Smoke tests passed for $env environment"
    return 0
}

# Function to update Nginx configuration
update_nginx_config() {
    local target_port=$1
    local target_env=$2

    log "Updating Nginx configuration to point to $target_env (port $target_port)..."

    # Check if Nginx config file exists
    if [ ! -f "$NGINX_CONFIG" ]; then
        log_warning "Nginx config not found at $NGINX_CONFIG. Skipping Nginx update."
        log_warning "You may need to manually configure your load balancer."
        return 0
    fi

    # Backup current config
    cp "$NGINX_CONFIG" "${NGINX_CONFIG}.backup-$(date +%Y%m%d-%H%M%S)"

    # Update proxy_pass directive
    sed -i "s/proxy_pass http:\/\/localhost:[0-9]*;/proxy_pass http:\/\/localhost:${target_port};/" "$NGINX_CONFIG"

    # Reload Nginx
    if command -v nginx > /dev/null 2>&1; then
        nginx -t && nginx -s reload
        log_success "Nginx configuration updated and reloaded"
    else
        log_warning "Nginx command not found. Config updated but not reloaded."
    fi

    return 0
}

# Function to backup database
backup_database() {
    log "Creating database backup before deployment..."

    # Create backup directory
    mkdir -p ./backups

    local backup_file="./backups/questdb-backup-$(date +%Y%m%d-%H%M%S).sql"

    # Use QuestDB pg_dump equivalent (if available)
    if command -v pg_dump > /dev/null 2>&1; then
        PGPASSWORD=quest pg_dump -h localhost -p 8812 -U admin -d qdb > "$backup_file" 2>/dev/null || true
        if [ -f "$backup_file" ] && [ -s "$backup_file" ]; then
            log_success "Database backup created: $backup_file"
        else
            log_warning "Database backup may have failed (file empty or not created)"
        fi
    else
        log_warning "pg_dump not available. Skipping database backup."
    fi
}

# Main deployment function
deploy() {
    log "============================================"
    log "Starting Blue-Green Deployment"
    log "============================================"

    # Get current active environment
    local active=$(get_active_env)
    local target_env
    local target_port
    local target_frontend_port
    local active_port

    if [ "$active" == "blue" ]; then
        target_env="green"
        target_port=$GREEN_PORT
        target_frontend_port=$GREEN_FRONTEND_PORT
        active_port=$BLUE_PORT
    else
        target_env="blue"
        target_port=$BLUE_PORT
        target_frontend_port=$BLUE_FRONTEND_PORT
        active_port=$GREEN_PORT
    fi

    log "Active environment: $active"
    log "Target environment: $target_env (port $target_port)"

    # Backup database
    backup_database

    # Build new Docker images (unless skipped)
    if [ "$SKIP_BUILD" = false ]; then
        log "Building Docker images for $target_env environment..."
        if ! docker-compose -f docker-compose.${target_env}.yml build; then
            log_error "Docker build failed"
            exit 1
        fi
        log_success "Docker images built successfully"
    else
        log_warning "Skipping build (--skip-build flag)"
    fi

    # Start target environment
    log "Starting $target_env environment..."
    if ! docker-compose -f docker-compose.${target_env}.yml up -d; then
        log_error "Failed to start $target_env environment"
        exit 1
    fi
    log_success "$target_env environment started"

    # Wait for backend health check
    if ! wait_for_health $target_port "backend-${target_env}"; then
        log_error "Backend health check failed for $target_env"
        if [ "$NO_ROLLBACK" = false ]; then
            log "Initiating automatic rollback..."
            docker-compose -f docker-compose.${target_env}.yml down
            exit 1
        else
            log_warning "Continuing despite health check failure (--no-rollback flag)"
        fi
    fi

    # Run smoke tests before switching traffic
    if ! run_smoke_tests $target_port $target_env; then
        log_error "Smoke tests failed for $target_env"
        if [ "$NO_ROLLBACK" = false ]; then
            log "Initiating automatic rollback..."
            docker-compose -f docker-compose.${target_env}.yml down
            exit 1
        else
            log_warning "Continuing despite smoke test failure (--no-rollback flag)"
        fi
    fi

    # Switch Nginx to target environment
    update_nginx_config $target_port $target_env

    log_success "Traffic switched to $target_env environment"

    # Final verification
    sleep 5
    if ! curl -sf ${HEALTH_CHECK_URL}:${target_port}/health > /dev/null 2>&1; then
        log_error "Post-switch health check failed!"
        if [ "$NO_ROLLBACK" = false ] && [ "$active" != "none" ]; then
            log "Initiating emergency rollback to $active..."
            update_nginx_config $active_port $active
            docker-compose -f docker-compose.${target_env}.yml down
            exit 1
        fi
    fi

    # Stop old environment
    if [ "$active" != "none" ]; then
        log "Waiting 30 seconds for connection draining..."
        sleep 30

        log "Stopping old environment: $active"
        docker-compose -f docker-compose.${active}.yml down
        log_success "Old environment stopped"
    fi

    log "============================================"
    log_success "DEPLOYMENT SUCCESSFUL"
    log "============================================"
    log "Active environment: $target_env"
    log "Backend URL: ${HEALTH_CHECK_URL}:${target_port}"
    log "Frontend URL: ${HEALTH_CHECK_URL}:${target_frontend_port}"
    log "Deployment log: $LOG_FILE"
}

# Trap errors
trap 'log_error "Deployment failed with error on line $LINENO"' ERR

# Run deployment
deploy
