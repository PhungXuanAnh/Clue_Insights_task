FROM python:3.11-slim

WORKDIR /app

ARG ENVIRONMENT=dev
ENV ENVIRONMENT=${ENVIRONMENT}

RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    pkg-config \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ requirements/

ENV MYSQLCLIENT_CFLAGS="-I/usr/include/mysql"
ENV MYSQLCLIENT_LDFLAGS="-L/usr/lib/x86_64-linux-gnu -lmysqlclient"

RUN if [ "$ENVIRONMENT" = "dev" ]; then \
        pip install --no-cache-dir -r requirements/dev.txt; \
    elif [ "$ENVIRONMENT" = "test" ]; then \
        pip install --no-cache-dir -r requirements/test.txt; \
    elif [ "$ENVIRONMENT" = "prod" ]; then \
        pip install --no-cache-dir -r requirements/prod.txt; \
    else \
        pip install --no-cache-dir -r requirements/base.txt; \
    fi

EXPOSE 5000

CMD ["python", "app.py"] 