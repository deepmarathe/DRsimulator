#!/bin/bash
docker exec postgres-db pg_dump -U myuser -d mydb > backup.sql
