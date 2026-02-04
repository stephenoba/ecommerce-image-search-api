#!/bin/bash
echo "Building Docker containers..."
docker-compose build

echo "Starting services..."
docker-compose up -d

echo "Waiting for database..."
sleep 5

echo "Running migrations..."
docker-compose exec web python manage.py migrate

echo "Creating superuser..."
docker-compose exec web python manage.py createsuperuser

echo "Setup complete! Access the API at http://localhost:8000"