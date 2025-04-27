#!/bin/bash

# Script to install environment-specific requirements

# Default to development environment if not specified
ENVIRONMENT=${1:-dev}

echo "Installing requirements for $ENVIRONMENT environment..."

if [ "$ENVIRONMENT" = "dev" ] || [ "$ENVIRONMENT" = "development" ]; then
    pip install -r requirements/dev.txt
    echo "Development requirements installed."
elif [ "$ENVIRONMENT" = "test" ] || [ "$ENVIRONMENT" = "testing" ]; then
    pip install -r requirements/test.txt
    echo "Testing requirements installed."
elif [ "$ENVIRONMENT" = "prod" ] || [ "$ENVIRONMENT" = "production" ]; then
    pip install -r requirements/prod.txt
    echo "Production requirements installed."
else
    echo "Unknown environment: $ENVIRONMENT"
    echo "Using default base.txt"
    pip install -r requirements/base.txt
fi

echo "Installation complete." 