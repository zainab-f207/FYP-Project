-- Password Reset Flow Migration
-- Add password reset token columns to users_info table

ALTER TABLE users_info ADD COLUMN password_reset_token VARCHAR(255) NULL;
ALTER TABLE users_info ADD COLUMN reset_token_expires_at TIMESTAMP NULL;

-- Add index for faster token lookups
CREATE INDEX idx_password_reset_token ON users_info(password_reset_token);
CREATE INDEX idx_reset_token_expires ON users_info(reset_token_expires_at);
