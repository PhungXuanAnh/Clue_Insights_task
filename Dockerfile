FROM python:3.11-slim

WORKDIR /app

# Set environment variable with a default value
ARG ENVIRONMENT=dev
ENV ENVIRONMENT=${ENVIRONMENT}

# Install system dependencies
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    pkg-config \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements directory
COPY requirements/ requirements/

# Set environment variables for mysqlclient build if pkg-config fails
ENV MYSQLCLIENT_CFLAGS="-I/usr/include/mysql"
ENV MYSQLCLIENT_LDFLAGS="-L/usr/lib/x86_64-linux-gnu -lmysqlclient"

# Install Python dependencies based on environment
RUN if [ "$ENVIRONMENT" = "dev" ]; then \
        pip install --no-cache-dir -r requirements/dev.txt; \
    elif [ "$ENVIRONMENT" = "test" ]; then \
        pip install --no-cache-dir -r requirements/test.txt; \
    elif [ "$ENVIRONMENT" = "prod" ]; then \
        pip install --no-cache-dir -r requirements/prod.txt; \
    else \
        pip install --no-cache-dir -r requirements/base.txt; \
    fi

# Copy the rest of the application
COPY . .

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["python", "app.py"] 