.PHONY: setup start stop test deploy clean

# Default target
all: setup

# Setup development environment
setup:
	@echo "Setting up development environment..."
	@test -d venv || python -m venv venv
	@. venv/bin/activate && pip install -r Backend/requirements.txt
	@. venv/bin/activate && pip install -e Backend
	@cd my-frontend && npm install
	@echo "Setup complete!"

# Start development environment
start:
	@echo "Starting development environment..."
	@./start-dev.sh

# Stop development environment
stop:
	@echo "Stopping development environment..."
	@docker-compose down

# Run all tests
test: test-backend test-frontend test-mobile

# Run backend tests
test-backend:
	@echo "Running backend tests..."
	@cd Backend && python -m pytest

# Run frontend tests
test-frontend:
	@echo "Running frontend tests..."
	@cd my-frontend && npm run lint

# Run mobile tests
test-mobile:
	@echo "Running mobile tests..."
	@cd tests && ./run-mobile-tests.sh

# Deploy to production
deploy:
	@echo "Deploying to production..."
	@python deploy.py --force-refresh

# Deploy only backend
deploy-backend:
	@echo "Deploying backend to production..."
	@python deploy.py --backend-only --force-refresh

# Deploy only frontend
deploy-frontend:
	@echo "Deploying frontend to production..."
	@python deploy.py --frontend-only --force-refresh

# Clean development environment
clean:
	@echo "Cleaning development environment..."
	@docker-compose down -v
	@rm -rf Backend/venv
	@rm -rf venv
	@rm -rf my-frontend/node_modules
	@rm -rf Backend/__pycache__
	@rm -rf Backend/tests/__pycache__
	@rm -rf Backend/toms_gym/__pycache__
	@rm -rf Backend/toms_gym/routes/__pycache__
	@echo "Cleanup complete!"

# Show help
help:
	@echo "Available commands:"
	@echo "  make setup         - Set up development environment"
	@echo "  make start         - Start development environment"
	@echo "  make stop          - Stop development environment"
	@echo "  make test          - Run all tests"
	@echo "  make test-backend  - Run backend tests"
	@echo "  make test-frontend - Run frontend tests"
	@echo "  make test-mobile   - Run mobile tests"
	@echo "  make deploy        - Deploy to production"
	@echo "  make deploy-backend - Deploy only backend"
	@echo "  make deploy-frontend - Deploy only frontend"
	@echo "  make clean         - Clean development environment"
	@echo "  make help          - Show this help message" 