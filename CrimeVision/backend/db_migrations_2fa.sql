-- Migration to add 2FA columns to users_info table
-- Run this after other migrations

ALTER TABLE users_info
ADD COLUMN two_factor_secret VARCHAR(255) DEFAULT NULL,
ADD COLUMN two_factor_enabled BOOLEAN DEFAULT FALSE;

-- Optional: Add index for performance if needed
-- CREATE INDEX idx_two_factor_enabled ON users_info(two_factor_enabled);
