#!/bin/bash

# PostgreSQL Development Setup Script
# Task 1.1: Database Migration to PostgreSQL
# Sets up local PostgreSQL for FastAPI development

set -e

echo "🐘 PostgreSQL Development Setup for FastAPI Backend"
echo "================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
POSTGRES_VERSION="15"
POSTGRES_USER="postgres"
POSTGRES_PASSWORD="dev_password_123"
POSTGRES_DB="balance_tracker"
POSTGRES_PORT="5432"
CONTAINER_NAME="fastapi_postgres_dev"

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker is not running. Please start Docker."
        exit 1
    fi
    
    log_success "Docker is installed and running"
}

setup_postgres_container() {
    log_info "Setting up PostgreSQL container..."
    
    # Check if container already exists
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        log_warning "Container $CONTAINER_NAME already exists"
        
        # Check if it's running
        if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            log_info "Container is already running"
            return 0
        else
            log_info "Starting existing container..."
            docker start $CONTAINER_NAME
            sleep 3
            return 0
        fi
    fi
    
    # Create new container
    log_info "Creating PostgreSQL container..."
    docker run -d \
        --name $CONTAINER_NAME \
        -e POSTGRES_USER=$POSTGRES_USER \
        -e POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
        -e POSTGRES_DB=$POSTGRES_DB \
        -p $POSTGRES_PORT:5432 \
        -v postgres_data:/var/lib/postgresql/data \
        postgres:$POSTGRES_VERSION
    
    log_success "PostgreSQL container created and started"
    
    # Wait for PostgreSQL to be ready
    log_info "Waiting for PostgreSQL to be ready..."
    sleep 10
    
    # Test connection
    for i in {1..30}; do
        if docker exec $CONTAINER_NAME pg_isready -U $POSTGRES_USER &> /dev/null; then
            log_success "PostgreSQL is ready!"
            break
        fi
        
        if [ $i -eq 30 ]; then
            log_error "PostgreSQL failed to start after 30 seconds"
            exit 1
        fi
        
        echo -n "."
        sleep 1
    done
}

install_python_dependencies() {
    log_info "Checking Python PostgreSQL dependencies..."
    
    # Check if psycopg2 is installed
    if python3 -c "import psycopg2" 2>/dev/null; then
        log_success "psycopg2 is already installed"
    else
        log_info "Installing psycopg2-binary..."
        pip install psycopg2-binary
        log_success "psycopg2-binary installed"
    fi
    
    # Check if other dependencies are available
    if python3 -c "import sqlalchemy" 2>/dev/null; then
        log_success "SQLAlchemy is available"
    else
        log_warning "SQLAlchemy not found - you may need to install it for advanced ORM features"
        echo "Install with: pip install sqlalchemy"
    fi
}

create_env_backup() {
    log_info "Creating .env backup..."
    
    if [ -f ".env" ]; then
        cp ".env" ".env.backup.$(date +%Y%m%d_%H%M%S)"
        log_success "Environment file backed up"
    else
        log_warning "No .env file found to backup"
    fi
}

update_env_config() {
    log_info "Updating environment configuration..."
    
    # Create or update .env file with PostgreSQL settings
    cat > .env.postgres << EOF
# =============================================================================
# Development Environment Configuration - PostgreSQL
# Updated by PostgreSQL setup script
# =============================================================================

# Environment
ENVIRONMENT=development
DEBUG=true

# Security - Development Keys (CHANGE FOR PRODUCTION)
SECRET_KEY=f19fb15492b88dbb703a5affeb215d308debaa49f91e47ce040e5ef8ad9be162
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30
JWT_REFRESH_EXPIRE_DAYS=7

# Password Requirements
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_NUMBERS=true
PASSWORD_REQUIRE_SPECIAL=false

# Database Configuration (PostgreSQL)
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/${POSTGRES_DB}
DATABASE_TYPE=postgresql

# API Configuration
API_V1_PREFIX=/api/v1
PROJECT_NAME=Balance Tracking System - Development
VERSION=1.0.0-dev

# CORS (Permissive for development)
CORS_ORIGINS=http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000
CORS_ALLOW_CREDENTIALS=true

# Rate Limiting (Relaxed for development)
RATE_LIMIT_ENABLED=true
RATE_LIMIT_AUTH_REQUESTS=10
RATE_LIMIT_TRADING_REQUESTS=100
RATE_LIMIT_INFO_REQUESTS=200
RATE_LIMIT_ADMIN_REQUESTS=5

# Redis Configuration (Development)
RATE_LIMIT_REDIS_URL=redis://localhost:6379/0
RATE_LIMIT_FALLBACK_TO_MEMORY=true

# Email Configuration (Development - Disabled)
EMAIL_ENABLED=false
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
SES_FROM_EMAIL=dev@localhost
SES_FROM_NAME=Trading System Dev

# Security Headers (Relaxed for development)
SECURITY_HEADERS_ENABLED=true
HTTPS_ONLY=false
HSTS_MAX_AGE=3600

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=detailed
LOG_FILE_ENABLED=false
LOG_FILE_PATH=logs/app.log

# Monitoring
HEALTH_CHECK_ENABLED=true
METRICS_ENABLED=true

# Security Configuration
MAX_REQUEST_SIZE=10485760
REQUEST_TIMEOUT=30

# PostgreSQL Development Setup
# Container: ${CONTAINER_NAME}
# Setup Date: $(date)
EOF

    log_success "PostgreSQL environment configuration created (.env.postgres)"
    echo ""
    echo "To use PostgreSQL configuration:"
    echo "  cp .env.postgres .env"
}

test_postgres_connection() {
    log_info "Testing PostgreSQL connection..."
    
    # Test with docker exec
    if docker exec $CONTAINER_NAME psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT version();" &> /dev/null; then
        log_success "PostgreSQL connection test successful"
        
        # Get version info
        version=$(docker exec $CONTAINER_NAME psql -U $POSTGRES_USER -d $POSTGRES_DB -t -c "SELECT version();" | head -1 | xargs)
        echo "  Version: $version"
    else
        log_error "PostgreSQL connection test failed"
        return 1
    fi
}

create_migration_instructions() {
    log_info "Creating migration instructions..."
    
    cat > POSTGRESQL_MIGRATION_GUIDE.md << EOF
# PostgreSQL Migration Guide

## Setup Completed ✅

Your PostgreSQL development environment is now ready!

### Connection Details
- **Host**: localhost
- **Port**: ${POSTGRES_PORT}
- **Database**: ${POSTGRES_DB}
- **Username**: ${POSTGRES_USER}
- **Password**: ${POSTGRES_PASSWORD}
- **Container**: ${CONTAINER_NAME}

### Next Steps

1. **Switch to PostgreSQL configuration:**
   \`\`\`bash
   cp .env.postgres .env
   \`\`\`

2. **Run the migration script:**
   \`\`\`bash
   python3 postgresql_migration.py
   \`\`\`

3. **Test your FastAPI application:**
   \`\`\`bash
   python3 main.py
   \`\`\`

### Managing PostgreSQL Container

- **Start container:**
  \`\`\`bash
  docker start ${CONTAINER_NAME}
  \`\`\`

- **Stop container:**
  \`\`\`bash
  docker stop ${CONTAINER_NAME}
  \`\`\`

- **Connect to PostgreSQL:**
  \`\`\`bash
  docker exec -it ${CONTAINER_NAME} psql -U ${POSTGRES_USER} -d ${POSTGRES_DB}
  \`\`\`

- **View logs:**
  \`\`\`bash
  docker logs ${CONTAINER_NAME}
  \`\`\`

- **Remove container and data (⚠️ DESTRUCTIVE):**
  \`\`\`bash
  docker stop ${CONTAINER_NAME}
  docker rm ${CONTAINER_NAME}
  docker volume rm postgres_data
  \`\`\`

### Database Management Commands

\`\`\`sql
-- List all databases
\\l

-- Connect to database
\\c ${POSTGRES_DB}

-- List all tables
\\dt

-- Describe table structure
\\d table_name

-- Show current database size
SELECT pg_size_pretty(pg_database_size('${POSTGRES_DB}'));
\`\`\`

### Troubleshooting

1. **Connection refused:**
   - Check if container is running: \`docker ps\`
   - Start container: \`docker start ${CONTAINER_NAME}\`

2. **Port already in use:**
   - Check what's using port ${POSTGRES_PORT}: \`lsof -i :${POSTGRES_PORT}\`
   - Stop other PostgreSQL instances or change port

3. **Permission errors:**
   - Ensure Docker has proper permissions
   - Try running with sudo (not recommended for regular use)

### Production Notes

For production deployment:
- Use managed PostgreSQL service (AWS RDS, Google Cloud SQL, etc.)
- Enable SSL connections
- Use strong passwords and proper user management
- Set up regular backups
- Configure connection pooling
- Monitor performance and logs

---
Generated on: $(date)
Container: ${CONTAINER_NAME}
EOF

    log_success "Migration guide created (POSTGRESQL_MIGRATION_GUIDE.md)"
}

print_summary() {
    echo ""
    echo "🎉 PostgreSQL Development Setup Complete!"
    echo "========================================"
    echo ""
    echo "📋 Summary:"
    echo "  • PostgreSQL container running: $CONTAINER_NAME"
    echo "  • Database: $POSTGRES_DB"
    echo "  • Port: $POSTGRES_PORT"
    echo "  • Configuration: .env.postgres"
    echo ""
    echo "🚀 Next Steps:"
    echo "  1. cp .env.postgres .env"
    echo "  2. python3 postgresql_migration.py"
    echo "  3. python3 main.py"
    echo ""
    echo "📖 See POSTGRESQL_MIGRATION_GUIDE.md for detailed instructions"
    echo ""
}

# Main execution
main() {
    echo "Starting PostgreSQL development setup..."
    echo ""
    
    check_docker
    create_env_backup
    setup_postgres_container
    install_python_dependencies
    update_env_config
    test_postgres_connection
    create_migration_instructions
    print_summary
    
    log_success "Setup completed successfully! 🐘"
}

# Handle script arguments
case "${1:-setup}" in
    "setup")
        main
        ;;
    "start")
        log_info "Starting PostgreSQL container..."
        docker start $CONTAINER_NAME
        log_success "PostgreSQL container started"
        ;;
    "stop")
        log_info "Stopping PostgreSQL container..."
        docker stop $CONTAINER_NAME
        log_success "PostgreSQL container stopped"
        ;;
    "restart")
        log_info "Restarting PostgreSQL container..."
        docker restart $CONTAINER_NAME
        log_success "PostgreSQL container restarted"
        ;;
    "status")
        if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            log_success "PostgreSQL container is running"
            docker exec $CONTAINER_NAME pg_isready -U $POSTGRES_USER
        else
            log_warning "PostgreSQL container is not running"
        fi
        ;;
    "connect")
        log_info "Connecting to PostgreSQL..."
        docker exec -it $CONTAINER_NAME psql -U $POSTGRES_USER -d $POSTGRES_DB
        ;;
    "logs")
        docker logs $CONTAINER_NAME
        ;;
    "remove")
        read -p "Are you sure you want to remove the PostgreSQL container and data? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker stop $CONTAINER_NAME 2>/dev/null || true
            docker rm $CONTAINER_NAME 2>/dev/null || true
            docker volume rm postgres_data 2>/dev/null || true
            log_success "PostgreSQL container and data removed"
        else
            log_info "Operation cancelled"
        fi
        ;;
    "help")
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  setup     - Initial setup (default)"
        echo "  start     - Start PostgreSQL container"
        echo "  stop      - Stop PostgreSQL container"
        echo "  restart   - Restart PostgreSQL container"
        echo "  status    - Check container status"
        echo "  connect   - Connect to PostgreSQL CLI"
        echo "  logs      - View container logs"
        echo "  remove    - Remove container and data (destructive)"
        echo "  help      - Show this help"
        ;;
    *)
        log_error "Unknown command: $1"
        echo "Use '$0 help' for available commands"
        exit 1
        ;;
esac
