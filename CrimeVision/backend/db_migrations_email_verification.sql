-- Email Verification Migration
-- Add email verification columns to users_info table

ALTER TABLE users_info ADD COLUMN is_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE users_info ADD COLUMN email_verification_token VARCHAR(255) NULL;
ALTER TABLE users_info ADD COLUMN token_expires_at TIMESTAMP NULL;

-- Add index for faster token lookups
CREATE INDEX idx_email_verification_token ON users_info(email_verification_token);
CREATE INDEX idx_token_expires_at ON users_info(token_expires_at);
