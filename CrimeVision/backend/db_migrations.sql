-- DB Migrations for SuperAdminDashboard Upgrades

-- Phase 1: Enhanced User & Admin Management
ALTER TABLE users_info ADD COLUMN activity_logs JSON DEFAULT NULL;

CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_username VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    target_type VARCHAR(50) NOT NULL, -- 'user', 'admin', 'system'
    target_id INT,
    details JSON,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_admin (admin_username),
    INDEX idx_action (action),
    INDEX idx_created (created_at)
);

-- Phase 3: System Monitoring & Management
CREATE TABLE IF NOT EXISTS system_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    log_type VARCHAR(50) NOT NULL, -- 'error', 'warning', 'info', 'performance'
    message TEXT NOT NULL,
    details JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_type (log_type),
    INDEX idx_created (created_at)
);

-- Phase 4: Security Enhancements
ALTER TABLE users_info ADD COLUMN last_login TIMESTAMP NULL;
ALTER TABLE users_info ADD COLUMN failed_attempts INT DEFAULT 0;
ALTER TABLE users_info ADD COLUMN two_factor_secret VARCHAR(32) NULL;
ALTER TABLE users_info ADD COLUMN two_factor_enabled BOOLEAN DEFAULT FALSE;

-- Phase 6: Communication & Notification System
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    type VARCHAR(50) NOT NULL, -- 'email', 'sms', 'in_app'
    recipient VARCHAR(100) NOT NULL,
    subject VARCHAR(255),
    message TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'sent', 'failed'
    priority VARCHAR(20) DEFAULT 'normal', -- 'low', 'normal', 'high', 'urgent'
    created_by VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP NULL,
    INDEX idx_type (type),
    INDEX idx_status (status),
    INDEX idx_created (created_at)
);

CREATE TABLE IF NOT EXISTS admin_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sender_username VARCHAR(50) NOT NULL,
    recipient_username VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_sender (sender_username),
    INDEX idx_recipient (recipient_username),
    INDEX idx_created (created_at)
);

-- Phase 8: Integration & API Management
CREATE TABLE IF NOT EXISTS api_keys (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    permissions JSON,
    rate_limit INT DEFAULT 1000, -- requests per hour
    created_by VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_key_hash (key_hash),
    INDEX idx_active (is_active)
);

-- Signup Flow: Email Verification
ALTER TABLE users_info ADD COLUMN is_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE users_info ADD COLUMN email_verification_token VARCHAR(255) NULL;
ALTER TABLE users_info ADD COLUMN token_expires_at TIMESTAMP NULL;
