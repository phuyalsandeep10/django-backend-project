#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting required services for ChatBoq...${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Function to check if a service is ready
check_service_ready() {
    local service_name=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    echo -e "${YELLOW}Waiting for $service_name to be ready...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if nc -z localhost $port 2>/dev/null; then
            echo -e "${GREEN}✓ $service_name is ready on port $port${NC}"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}✗ $service_name failed to start within $((max_attempts * 2)) seconds${NC}"
    return 1
}

# Function to check Kafka specifically (more complex health check)
check_kafka_ready() {
    local max_attempts=30
    local attempt=1
    
    echo -e "${YELLOW}Waiting for Kafka to be ready...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        # Check if Kafka container is running and healthy
        if docker-compose ps kafka | grep -q "Up" && \
           docker-compose exec -T kafka kafka-topics --bootstrap-server localhost:9092 --list >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Kafka is ready${NC}"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}✗ Kafka failed to start within $((max_attempts * 2)) seconds${NC}"
    return 1
}

# Start services asynchronously
echo -e "${BLUE}Starting Kafka, Zookeeper, and Redis in parallel...${NC}"

# Start all services in background
docker-compose up -d kafka zookeeper redis &
DOCKER_PID=$!

# Wait for docker-compose to finish starting containers
wait $DOCKER_PID

# Check if services started successfully
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to start services with docker-compose${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All containers started successfully${NC}"

# Wait for services to be ready in parallel
echo -e "${BLUE}Checking service readiness...${NC}"

# Start health checks in parallel
check_kafka_ready &
KAFKA_PID=$!

check_service_ready "Redis" 6379 &
REDIS_PID=$!

# Wait for all health checks to complete
wait $KAFKA_PID
KAFKA_RESULT=$?

wait $REDIS_PID
REDIS_RESULT=$?

# Check if all services are ready
if [ $KAFKA_RESULT -eq 0 ] && [ $REDIS_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ All services are ready!${NC}"
else
    echo -e "${RED}✗ Some services failed to start properly${NC}"
    if [ $KAFKA_RESULT -ne 0 ]; then
        echo -e "${RED}  - Kafka failed to start${NC}"
    fi
    if [ $REDIS_RESULT -ne 0 ]; then
        echo -e "${RED}  - Redis failed to start${NC}"
    fi
    exit 1
fi

# Display service status
echo ""
echo -e "${BLUE}Service Status:${NC}"
docker-compose ps

echo ""
echo -e "${GREEN}Services started successfully!${NC}"
echo ""
echo -e "${BLUE}Service endpoints:${NC}"
echo "  Kafka:"
echo "    - From host machine: localhost:29092"
echo "    - From Docker containers: kafka:9092"
echo "  Kafka UI: http://localhost:8080"
echo "  Redis: localhost:6379"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  To start your application, run:"
echo "    fastapi dev src/main.py"
echo ""
echo "  To start Celery worker, run:"
echo "    celery -A src.config.celery worker --loglevel=info"
echo ""
echo "  To start Celery beat (for periodic tasks), run:"
echo "    celery -A src.config.celery beat --loglevel=info"
echo ""
echo "  Or start both with docker-compose:"
echo "    docker-compose up -d celery_worker celery_beat" 