#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Run database migrations
echo "Running database migrations..."
flask db upgrade

# Start the Flask app using Gunicorn, specifying the factory function
echo "Starting web server..."
exec gunicorn 'run:create_app()'
