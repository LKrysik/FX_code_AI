#!/bin/bash
set -e

# Emergency Rollback Script for FX Trading System
# Quickly switch back to the previous environment
# Usage: ./rollback.sh [--force] [--restore-db]

# Configuration
BLUE_PORT=8080
GREEN_PORT=8081
HEALTH_CHECK_URL="http://localhost"
MAX_HEALTH_RETRIES=10
HEALTH_CHECK_INTERVAL=5
NGINX_CONFIG="/etc/nginx/conf.d/trading.conf"
LOG_FILE="./logs/rollback-$(date +%Y%m%d-%H%M%S).log"

# Command line options
FORCE_ROLLBACK=false
RESTORE_DB=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE_ROLLBACK=true
            shift
            ;;
        --restore-db)
            RESTORE_DB=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--force] [--restore-db]"
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
    cp "$NGINX_CONFIG" "${NGINX_CONFIG}.rollback-backup-$(date +%Y%m%d-%H%M%S)"

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

# Function to restore database from backup
restore_database() {
    log "Restoring database from most recent backup..."

    # Find most recent backup
    local backup_file=$(ls -t ./backups/questdb-backup-*.sql 2>/dev/null | head -n 1)

    if [ -z "$backup_file" ]; then
        log_error "No backup file found in ./backups/"
        return 1
    fi

    log "Using backup file: $backup_file"

    # Restore using psql
    if command -v psql > /dev/null 2>&1; then
        PGPASSWORD=quest psql -h localhost -p 8812 -U admin -d qdb < "$backup_file"
        log_success "Database restored from backup"
        return 0
    else
        log_error "psql not available. Cannot restore database."
        return 1
    fi
}

# Main rollback function
rollback() {
    log "============================================"
    log "Starting Emergency Rollback"
    log "============================================"

    # Confirm rollback (unless --force)
    if [ "$FORCE_ROLLBACK" = false ]; then
        echo ""
        echo -e "${RED}WARNING: You are about to perform an emergency rollback!${NC}"
        echo "This will switch traffic to the previous environment."
        read -p "Are you sure you want to continue? (yes/no): " confirm

        if [ "$confirm" != "yes" ]; then
            log "Rollback cancelled by user"
            exit 0
        fi
    fi

    # Get current active environment
    local active=$(get_active_env)
    local target_env
    local target_port
    local active_port

    if [ "$active" == "blue" ]; then
        target_env="green"
        target_port=$GREEN_PORT
        active_port=$BLUE_PORT
    elif [ "$active" == "green" ]; then
        target_env="blue"
        target_port=$BLUE_PORT
        active_port=$GREEN_PORT
    else
        log_error "No active environment detected. Cannot rollback."
        exit 1
    fi

    log "Current active environment: $active (port $active_port)"
    log "Rolling back to: $target_env (port $target_port)"

    # Restore database if requested
    if [ "$RESTORE_DB" = true ]; then
        if ! restore_database; then
            log_error "Database restore failed"
            if [ "$FORCE_ROLLBACK" = false ]; then
                exit 1
            else
                log_warning "Continuing rollback despite database restore failure (--force flag)"
            fi
        fi
    fi

    # Check if target environment exists
    if ! docker ps -a --format '{{.Names}}' | grep -q "trading-backend-${target_env}"; then
        log "Target environment container not found. Starting from scratch..."
        if ! docker-compose -f docker-compose.${target_env}.yml up -d; then
            log_error "Failed to start target environment"
            exit 1
        fi
    else
        # Start target environment (it may be stopped)
        log "Starting $target_env environment..."
        if ! docker-compose -f docker-compose.${target_env}.yml start; then
            log_warning "Failed to start existing containers. Recreating..."
            docker-compose -f docker-compose.${target_env}.yml down
            docker-compose -f docker-compose.${target_env}.yml up -d
        fi
    fi

    # Wait for health check
    if ! wait_for_health $target_port "backend-${target_env}"; then
        log_error "Target environment failed health check"
        if [ "$FORCE_ROLLBACK" = false ]; then
            log_error "Rollback aborted. Previous environment is unhealthy."
            log_error "Manual intervention required!"
            exit 1
        else
            log_warning "Continuing rollback despite health check failure (--force flag)"
        fi
    fi

    # Switch Nginx back to target environment
    update_nginx_config $target_port $target_env

    log_success "Traffic switched back to $target_env environment"

    # Verify health after switch
    sleep 5
    if ! curl -sf ${HEALTH_CHECK_URL}:${target_port}/health > /dev/null 2>&1; then
        log_error "Post-rollback health check failed!"
        log_error "System may be in degraded state. Check logs immediately."
    else
        log_success "Post-rollback health check passed"
    fi

    # Stop failed environment
    log "Stopping failed environment: $active"
    docker-compose -f docker-compose.${active}.yml down
    log_success "Failed environment stopped"

    log "============================================"
    log_success "ROLLBACK COMPLETE"
    log "============================================"
    log "Active environment: $target_env"
    log "Backend URL: ${HEALTH_CHECK_URL}:${target_port}"
    log "Rollback log: $LOG_FILE"
    log ""
    log_warning "IMPORTANT: Investigate the root cause of the deployment failure"
    log_warning "Check logs in ./logs/ directory"
}

# Trap errors
trap 'log_error "Rollback failed with error on line $LINENO"' ERR

# Run rollback
rollback
