run:
		@echo "Starting fastapi"
		fastapi dev src/main.py
celery:
		@echo "Starting celery"
		celery -A src.config.celery worker -l DEBUG -P solo


