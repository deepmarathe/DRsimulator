#!/bin/bash

# Stop and remove existing postgres container if it exists
docker stop postgres-db 2>/dev/null || true
docker rm postgres-db 2>/dev/null || true

# Sleep to let Docker clean up
sleep 3

# Remove and recreate volume
docker volume rm dr-simulator_pgdata 2>/dev/null || true
docker volume create dr-simulator_pgdata

# Detect the Compose-managed network name
NETWORK_NAME=$(docker network ls --format "{{.Name}}" | grep dr-simulator_drnet || echo bridge)

# Start new PostgreSQL container on the same network
docker run -d --name postgres-db \
  --network "$NETWORK_NAME" \
  -e POSTGRES_PASSWORD=mypass \
  -e POSTGRES_USER=myuser \
  -e POSTGRES_DB=mydb \
  -v dr-simulator_pgdata:/var/lib/postgresql/data \
  postgres:15

# Wait for DB to boot up
sleep 5

# Restore the backup
cat backup.sql | docker exec -i postgres-db psql -U myuser -d mydb
