# Optimized Subscription Management API

A RESTful API for managing user subscriptions with optimized SQL queries.

## Overview

This project is a Flask-based API that provides:
- User registration and authentication
- Subscription plan management
- User subscription handling (subscribe, upgrade, cancel)
- Optimized SQL queries for subscription-related operations
- Multiple API versions with varying performance optimizations

## API Versions

### API v1
Standard API with ORM-based database access.

### API v2
Optimized API with raw SQL queries for improved performance in high-load scenarios.
See `app/api/v2/README.md` for detailed documentation on the v2 API.

## Technologies Used

- Python 3.11
- Flask and Flask-RESTx
- SQLAlchemy ORM with raw SQL optimizations
- MySQL database
- JWT authentication
- Docker and Docker Compose

## Setup and Installation

### Prerequisites

- Python 3.11
- Docker and Docker Compose
- MySQL client (for local development without Docker)
- Make (for using the Makefile commands)

### Using Docker (Recommended)

1. Clone the repository:
   ```
   git clone <repository-url>
   cd subscription-management-api
   ```

2. Use Make commands to set up and run the application:
   ```
   # Set up the development environment
   make setup
   
   # Run the development server
   make run
   ```

3. Access the API documentation at:
   ```
   http://localhost:5000/api/docs
   ```

### Local Development with Virtual Environment

1. Clone the repository:
   ```
   git clone <repository-url>
   cd subscription-management-api
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   # For development
   pip install -r requirements/dev.txt
   
   # For testing
   pip install -r requirements/test.txt
   
   # For production
   pip install -r requirements/prod.txt
   
   # Or use the helper script
   ./install_requirements.sh dev  # Options: dev, test, prod
   ```

4. Set up environment variables:
   ```
   cp app/.env.example .env
   # Edit .env to set database connection details and other settings
   ```

5. Run the development server:
   ```
   flask run
   ```

## Testing

Run tests using the Makefile:

```bash
# Run all tests
make test

# Run a specific test or test directory
TEST_CASE=tests/unit/test_config.py make test
```

The test command:
1. Starts a dedicated test database container
2. Runs the tests in an isolated environment
3. Automatically cleans up all test containers and volumes when done

For test coverage:

```
pytest --cov=app tests/
```

## Sample Data Creation

To create sample subscription plans for testing and development:

```bash
# Copy the sample data creation script to the container
docker cp create_sample_plans.py clue_insights_task-app-1:/app/

# Run the script inside the container
docker exec -it clue_insights_task-app-1 python /app/create_sample_plans.py
```

This will create the following subscription plans if they don't already exist:
- Free Plan (monthly, $0)
- Basic Plan (monthly, $9.99)
- Pro Plan (monthly, $29.99)
- Basic Plan (Annual, $99.99)
- Pro Plan (Annual, $299.99)

You can verify the created plans by accessing the API endpoint:
```
curl -X GET "http://localhost:5000/api/plans/" -H "accept: application/json" | jq
```

To create an admin user for testing:
```bash
# Copy the admin user creation script to the container
docker cp create_admin.py clue_insights_task-app-1:/app/

# Run the script inside the container
docker exec -it clue_insights_task-app-1 python /app/create_admin.py
```

The default admin credentials are:
- Username: admin
- Password: admin123

## Project Structure

```
├── app/                    # Application package
│   ├── api/                # API endpoints
│   ├── auth/               # Authentication logic
│   ├── models/             # Database models
│   ├── utils/              # Utility functions
│   └── config/             # Configuration modules
├── requirements/           # Requirements for different environments
│   ├── base.txt            # Base dependencies
│   ├── dev.txt             # Development dependencies
│   ├── test.txt            # Testing dependencies
│   └── prod.txt            # Production dependencies
├── tests/                  # Test suite
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests
├── docs/                   # Documentation files
│   └── profiling_queries.md # Guide for query profiling
├── init-db/                # Database initialization scripts
├── docker-compose.yml      # Docker Compose configuration for development
├── docker-compose.test.yml # Docker Compose configuration for testing
├── Makefile                # Makefile with common commands
├── app.py                  # Application entry point
├── Dockerfile              # Docker build instructions
└── install_requirements.sh # Script to install requirements
```

## Makefile Commands

This project includes several helpful make commands to streamline development:

- `make setup`: Sets up the development environment
- `make run`: Starts the development server
- `make test`: Runs all tests (or a specific test with `TEST_CASE=path/to/test.py`)
- `make test-clean`: Removes all test containers and volumes
- `make db-init`: Initializes database migrations (creates migrations directory)
- `make db-migrate`: Generates a new migration (use with `message="Migration description"`)
- `make db-upgrade`: Applies migrations to update the database schema

## Query Optimization Strategies

This API implements the following optimization strategies:

1. **Custom SQL for performance-critical operations:**
   - Raw SQL queries in v2 API endpoints for direct database access
   - Optimized JOIN operations with careful index utilization
   - Single-query data retrieval reducing round trips to the database

2. **Strategic indexing for common query patterns**
3. **Efficient pagination implemented at the database level**
4. **JSON serialization optimizations for Decimal and DateTime types**

For examples of these optimizations, see:
- `app/utils/sql_optimizations.py` - Raw SQL implementations
- `app/api/v2/` - Optimized API endpoints using raw SQL

See the API documentation for detailed explanations of specific optimizations.

## Query Profiling

The development environment includes Flask-DebugToolbar for profiling SQL queries:

1. Access any HTML endpoint (like `/api/docs`) in development mode
2. Use the SQLAlchemy panel to identify slow queries
3. Use the Profiler panel to analyze execution times

For JSON API endpoints, you can use the SQLAlchemy echo feature which logs all SQL to the console:
```bash
# View the most recent SQL queries and execution times
docker logs --tail 100 clue_insights_task-app-1
```

See `docs/profiling_queries.md` for detailed instructions on profiling.