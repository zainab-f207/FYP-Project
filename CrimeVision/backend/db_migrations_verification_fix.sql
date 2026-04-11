-- Fix Verification Status and Add Missing Columns
-- Update existing users to verified status and add missing columns

-- Add missing verification columns if they don't exist
ALTER TABLE users_info ADD COLUMN IF NOT EXISTS verification_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE users_info ADD COLUMN IF NOT EXISTS verified_at TIMESTAMP NULL;
ALTER TABLE users_info ADD COLUMN IF NOT EXISTS verified_by INT NULL;

-- Update existing users to verified status (assuming they are all verified for now)
UPDATE users_info SET
    verification_status = 'verified',
    verified_at = CURRENT_TIMESTAMP,
    verified_by = 1,  -- Assuming admin ID 1
    is_verified = TRUE
WHERE verification_status = 'pending' OR is_verified = FALSE;

-- Ensure two_factor columns are properly initialized (they should be NULL and FALSE by default)
-- No changes needed here as they are already in the schema
