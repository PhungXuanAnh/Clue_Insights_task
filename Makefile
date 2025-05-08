.PHONY: help setup run test test-clean db-init db-migrate db-upgrade

# Default target
help:
	@echo "Available commands:"
	@echo "  make setup    - Set up the development environment"
	@echo "  make run      - Run the development server"
	@echo "  make test     - Run tests (use TEST_CASE=path/to/test.py to run specific tests)"
	@echo "  make test-clean - Remove all test containers and volumes"
	@echo "  make db-init  - Initialize database migrations"
	@echo "  make db-migrate - Generate a new migration"
	@echo "  make db-upgrade - Apply migrations to the database"

# Set up development environment
setup:
	@echo "Setting up development environment..."
	docker compose build
	docker compose up -d db
	@echo "Development environment set up successfully."

# Run development server
run:
	@echo "Starting development server..."
	docker compose up

test-build-image:
	@echo "Building test image..."
	docker compose -f docker-compose.test.yml build
	@echo "Test image built successfully."

test:
	@echo "Running tests..."
	@echo "TEST_CASE = ${TEST_CASE}"
	
	# Start test database first and wait for it to be ready
	docker compose -f docker-compose.test.yml up -d test-db
	@echo "Waiting for test database to be ready..."
	@MAX_RETRIES=30; \
	RETRIES=0; \
	until docker exec clue_insights_task-test-db-1 mysqladmin ping -h localhost -u user -ppassword --silent || [ $$RETRIES -eq $$MAX_RETRIES ]; do \
		echo "Waiting for database to be ready... $$RETRIES/$$MAX_RETRIES"; \
		sleep 1; \
		RETRIES=$$((RETRIES+1)); \
	done; \
	if [ $$RETRIES -eq $$MAX_RETRIES ]; then \
		echo "Database did not become ready in time"; \
		exit 1; \
	fi; \
	echo "Database is ready!"
	
	# Then start test app and run tests
	TEST_CASE=${TEST_CASE} docker compose -f docker-compose.test.yml up --abort-on-container-exit --menu=false test-app
	
	# Clean up after tests
	@echo "Tests completed. Cleaning up..."
	make test-clean

# Clean up test containers and volumes
test-clean:
	@echo "Removing test containers and volumes..."
	docker compose -f docker-compose.test.yml down -v
	@echo "Test cleanup completed."

# Initialize database migrations
db-init:
	@echo "Initializing database migrations..."
	docker compose exec app flask db init
	@echo "Migration repository created."

# Generate a new migration
db-migrate:
	@echo "Generating a new migration..."
	docker compose exec app flask db migrate -m "$(message)"
	@echo "Migration created. Review the generated migrations before applying."

# Apply migrations to the database
db-upgrade:
	@echo "Applying migrations to the database..."
	docker compose exec app flask db upgrade
	@echo "Database upgraded successfully."

db-show-tables:
	@echo "Showing all tables in the database..."
	docker exec -it clue_insights_task-db-1 mysql -uuser -ppassword -e "USE subscription_dev_db; SHOW TABLES;"
	@echo "Tables displayed successfully."

db-show-indexes:
	@echo "Showing all indexes in the database..."
	docker exec -it clue_insights_task-db-1 mysql -uuser -ppassword -e "USE subscription_dev_db; SHOW INDEXES FROM users;"
	docker exec -it clue_insights_task-db-1 mysql -uuser -ppassword -e "USE subscription_dev_db; SHOW INDEXES FROM subscription_plans;"
	docker exec -it clue_insights_task-db-1 mysql -uuser -ppassword -e "USE subscription_dev_db; SHOW INDEXES FROM user_subscriptions;"
	@echo "Indexes displayed successfully."

db-create-sample-data:
	@echo "Creating sample data..."
	docker exec -it clue_insights_task-app-1 python scripts/create_sample_plans.py
	docker exec -it clue_insights_task-app-1 python scripts/create_users_data.py --number_user=100
	docker exec -it clue_insights_task-app-1 python scripts/create_admin.py
	@echo "Sample data created successfully."

