# Optimized Subscription Management API

A RESTful API for managing user subscriptions with optimized SQL queries.

## Overview

This project is a Flask-based API that provides:
- User registration and authentication
- Subscription plan management
- User subscription handling (subscribe, upgrade, cancel)
- Optimized SQL queries for subscription-related operations

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

1. Custom SQL for performance-critical operations
2. Strategic indexing for common query patterns
3. Optimized JOIN operations to minimize database load
4. Efficient pagination for list operations

See the API documentation for detailed explanations of specific optimizations.