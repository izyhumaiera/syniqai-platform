-- SyniqAI PostgreSQL Setup Script
-- Run this script to create the database and user for SyniqAI

-- Create database
CREATE DATABASE syniqai_metadata;

-- Create user with password
CREATE USER syniqai_user WITH PASSWORD 'syniqai_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE syniqai_metadata TO syniqai_user;

-- Connect to syniqai_metadata database (you need to run: \c syniqai_metadata)
-- Then grant schema privileges:
GRANT ALL PRIVILEGES ON SCHEMA public TO syniqai_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO syniqai_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO syniqai_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO syniqai_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO syniqai_user;

-- Display success message
SELECT 'SyniqAI PostgreSQL setup complete!' as status;
