-- PostgreSQL initialization script for COTAI

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS cotai;
CREATE SCHEMA IF NOT EXISTS audit;

-- Set default schema
SET search_path TO cotai, public;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA cotai TO cotai;
GRANT ALL PRIVILEGES ON SCHEMA audit TO cotai;