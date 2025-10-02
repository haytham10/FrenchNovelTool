.PHONY: help build up down logs clean dev prod test lint

# Default target
help:
	@echo "French Novel Tool - Docker Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  build       Build all Docker images"
	@echo "  up          Start all services (production)"
	@echo "  down        Stop all services"
	@echo "  logs        Show logs from all services"
	@echo "  clean       Remove containers, volumes, and images"
	@echo "  dev         Start development environment"
	@echo "  prod        Start production environment"
	@echo "  test        Run backend tests"
	@echo "  lint        Run linters"
	@echo "  shell-be    Open shell in backend container"
	@echo "  shell-fe    Open shell in frontend container"

# Build Docker images
build:
	docker-compose build

# Start production environment
up:
	docker-compose up -d

# Start production environment (alias)
prod: up

# Start development environment
dev:
	docker-compose -f docker-compose.dev.yml up

# Stop all services
down:
	docker-compose down
	docker-compose -f docker-compose.dev.yml down

# Show logs
logs:
	docker-compose logs -f

# Clean everything
clean:
	docker-compose down -v --rmi all
	docker-compose -f docker-compose.dev.yml down -v --rmi all

# Run backend tests
test:
	docker-compose exec backend pytest

# Run linters
lint:
	docker-compose exec backend flake8 app/
	docker-compose exec frontend npm run lint

# Open backend shell
shell-be:
	docker-compose exec backend /bin/bash

# Open frontend shell
shell-fe:
	docker-compose exec frontend /bin/sh

# Database migrations
migrate:
	docker-compose exec backend flask db upgrade

# Create new migration
migration:
	@read -p "Enter migration message: " message; \
	docker-compose exec backend flask db migrate -m "$$message"

# Restart services
restart:
	docker-compose restart

# View service status
status:
	docker-compose ps

# Pull latest images
pull:
	docker-compose pull

# Remove unused Docker resources
prune:
	docker system prune -af --volumes

