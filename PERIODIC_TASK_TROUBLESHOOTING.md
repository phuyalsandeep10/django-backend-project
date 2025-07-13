# Periodic Task Troubleshooting Guide

## Problem
The `setup_periodic_tasks` function is not calling `consume_kafka_messages_batch` properly.

## Root Causes and Solutions

### 1. Missing Celery Beat Service
**Problem**: Periodic tasks require Celery Beat to be running.

**Solution**: 
- Added `celery_beat` service to `docker-compose.yml`
- Start both worker and beat: `docker-compose up -d celery_worker celery_beat`

### 2. Incorrect Periodic Task Configuration
**Problem**: Using `@celery_app.on_after_configure.connect` decorator was not working properly.

**Solution**: 
- Moved periodic task configuration to `celery.py` using `beat_schedule`
- Removed the problematic `setup_periodic_tasks` function

### 3. Missing Celery Configuration
**Problem**: Celery app was missing proper configuration for periodic tasks.

**Solution**: 
- Added complete Celery configuration in `src/config/celery.py`
- Configured `beat_schedule` with proper task registration

## How to Test

### 1. Start Services
```bash
# Start all services including Celery Beat
docker-compose up -d

# Or start just the required services
docker-compose up -d kafka zookeeper redis celery_worker celery_beat
```

### 2. Check Celery Beat Logs
```bash
# Check if beat is running and scheduling tasks
docker-compose logs celery_beat

# You should see logs like:
# [2024-01-01 12:00:00,000: INFO/MainProcess] Scheduler: Sending due task consume-kafka-messages-every-10s
```

### 3. Check Celery Worker Logs
```bash
# Check if worker is processing tasks
docker-compose logs celery_worker

# You should see logs like:
# [PERIODIC TASK] Starting consume_kafka_messages_batch...
```

### 4. Manual Test
```bash
# Run the test script to manually trigger the task
python test_periodic_task.py
```

## Debugging Steps

### 1. Verify Kafka Connection
- Check if Kafka is running: `docker-compose ps kafka`
- Verify Kafka UI: http://localhost:8080
- Check Kafka logs: `docker-compose logs kafka`

### 2. Verify Redis Connection
- Check if Redis is running: `docker-compose ps redis`
- Test Redis connection: `docker exec -it chatboq-service-redis-1 redis-cli ping`

### 3. Verify Task Registration
- Check Celery worker logs for task registration
- Look for: `[tasks] . src.tasks.message_task.consume_kafka_messages_batch`

### 4. Check Database Connection
- Verify database is accessible
- Check if Message model is properly imported

## Common Issues

### Issue 1: "No module named 'src.tasks'"
**Solution**: Ensure the Celery app includes the tasks module:
```python
celery_app = Celery(__name__, include=["src.tasks"])
```

### Issue 2: "Kafka connection failed"
**Solution**: 
- Check Kafka bootstrap servers configuration
- Ensure Kafka is running and accessible
- Verify network connectivity between containers

### Issue 3: "Task not found"
**Solution**: 
- Restart Celery worker after code changes
- Check task name in beat_schedule matches actual task function

### Issue 4: "Database connection failed"
**Solution**: 
- Check database URL configuration
- Ensure database is running and accessible
- Verify database migrations are applied

## Monitoring

### Flower Dashboard
Access Flower at http://localhost:5555 to monitor:
- Task execution
- Periodic task schedule
- Worker status

### Logs
Monitor logs for periodic task execution:
```bash
# Follow all logs
docker-compose logs -f

# Follow specific service
docker-compose logs -f celery_worker celery_beat
```

## Expected Behavior

When working correctly, you should see:
1. Celery Beat logs showing task scheduling every 10 seconds
2. Celery Worker logs showing task execution with `[PERIODIC TASK]` prefix
3. Kafka polling messages in the logs
4. Database insertion logs when messages are found
5. Task completion logs

## Configuration Files Changed

1. `src/config/celery.py` - Added beat_schedule configuration
2. `src/tasks/message_task.py` - Removed setup_periodic_tasks, added debugging
3. `docker-compose.yml` - Added celery_beat service
4. `start_services.sh` - Updated instructions
5. `test_periodic_task.py` - Added manual test script 