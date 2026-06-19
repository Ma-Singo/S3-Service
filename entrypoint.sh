#!/bin/bash
# entrypoint.sh

echo "Running database migrations..."
alembic upgrade head

echo "Starting application..."
exec "$@"