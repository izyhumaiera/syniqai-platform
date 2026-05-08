-- STEP 1: Create Database and User
-- Run this while connected to the "postgres" database

-- Create the database
CREATE DATABASE syniqai_metadata;

-- Create the user
CREATE USER syniqai_user WITH PASSWORD 'syniqai_password';

-- Grant database-level privileges
GRANT ALL PRIVILEGES ON DATABASE syniqai_metadata TO syniqai_user;

-- Verify database was created
SELECT datname FROM pg_database WHERE datname = 'syniqai_metadata';

-- You should see: syniqai_metadata

-- NEXT: Disconnect from "postgres" and connect to "syniqai_metadata" database
-- Then run create_silver_tables.sql
