#!/bin/bash

echo "Waiting for database to be ready..."
sleep 5

# Apply the user table migration
PGPASSWORD=test psql -h localhost -p 5433 -U postgres -d postgres -f toms_gym/migrations/create_user_table.sql

echo "Database initialization completed." 