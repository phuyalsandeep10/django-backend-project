#!/bin/bash

echo "Starting required services for ChatBoq..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Start Kafka and related services
echo "Starting Kafka, Zookeeper, and Redis..."
docker-compose up -d kafka zookeeper redis

# Wait for Kafka to be ready
echo "Waiting for Kafka to be ready..."
sleep 10

# Check if Kafka is running
echo "Checking Kafka status..."
docker-compose ps kafka

echo "Services started successfully!"
echo ""
echo "Kafka is available at:"
echo "  - From host machine: localhost:29092"
echo "  - From Docker containers: kafka:9092"
echo ""
echo "Kafka UI is available at: http://localhost:8080"
echo "Redis is available at: localhost:6379"
echo ""
echo "To start your application, run:"
echo "  python -m src.main"
echo ""
echo "To start Celery worker, run:"
echo "  celery -A src.config.celery worker --loglevel=info"
echo ""
echo "To start Celery beat (for periodic tasks), run:"
echo "  celery -A src.config.celery beat --loglevel=info"
echo ""
echo "Or start both with docker-compose:"
echo "  docker-compose up -d celery_worker celery_beat" 