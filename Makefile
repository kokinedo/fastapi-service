.PHONY: help install lint format clean run dev migrate

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements.txt
	pip install pre-commit
	pre-commit install

lint: ## Run linting
	flake8 app
	mypy app

format: ## Format code
	black app
	isort app

format-check: ## Check code formatting
	black --check app
	isort --check-only app

clean: ## Clean up cache files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf htmlcov

run: ## Run the application
	uvicorn app.main:app --host 0.0.0.0 --port 8000

dev: ## Run the application in development mode
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

migrate-init: ## Initialize Alembic migrations
	alembic init alembic

migrate-create: ## Create a new migration
	alembic revision --autogenerate -m "$(msg)"

migrate-up: ## Apply migrations
	alembic upgrade head

migrate-down: ## Rollback one migration
	alembic downgrade -1

docker-build: ## Build Docker image
	docker build -t task-management-service .

docker-run: ## Run with Docker Compose
	docker-compose up -d

docker-stop: ## Stop Docker Compose
	docker-compose down

docker-logs: ## View Docker logs
	docker-compose logs -f

db-reset: ## Reset database (WARNING: This will delete all data)
	@echo "This will delete all data in the database. Are you sure? [y/N]" && read ans && [ $${ans:-N} = y ]
	docker-compose down -v
	docker-compose up -d postgres
	sleep 5
	alembic upgrade head