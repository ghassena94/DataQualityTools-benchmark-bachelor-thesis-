-- Executed once by the postgres container on first startup.
-- The "rein" database and "reinuser" are already created by the
-- POSTGRES_* environment variables in docker-compose.yml.
-- This script adds the secondary "holo" database for HoloClean.

CREATE DATABASE holo;
CREATE USER holocleanuser WITH PASSWORD 'abcd1234';
GRANT ALL PRIVILEGES ON DATABASE holo TO holocleanuser;
