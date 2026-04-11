-- Migration to add Google OAuth support
-- Add google_id column to users_info table

ALTER TABLE users_info ADD COLUMN google_id VARCHAR(255) UNIQUE NULL;
ALTER TABLE users_info ADD COLUMN email_verified BOOLEAN DEFAULT FALSE;

-- Add index for better performance on Google ID lookups
CREATE INDEX idx_google_id ON users_info (google_id);
