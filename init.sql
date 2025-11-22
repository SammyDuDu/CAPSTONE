-- KoSPA Database Initialization Script
-- This script runs automatically when PostgreSQL container starts for the first time

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Progress table (stores user's highest score per sound)
CREATE TABLE IF NOT EXISTS progress (
    id SERIAL PRIMARY KEY,
    userid INTEGER REFERENCES users(id) ON DELETE CASCADE,
    sound VARCHAR(10) NOT NULL,
    progress INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(userid, sound)
);

-- Formants table (stores user calibration data)
CREATE TABLE IF NOT EXISTS formants (
    id SERIAL PRIMARY KEY,
    userid INTEGER REFERENCES users(id) ON DELETE CASCADE,
    sound VARCHAR(10) NOT NULL,
    f1_mean FLOAT,
    f1_std FLOAT,
    f2_mean FLOAT,
    f2_std FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(userid, sound)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_progress_userid ON progress(userid);
CREATE INDEX IF NOT EXISTS idx_formants_userid ON formants(userid);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
