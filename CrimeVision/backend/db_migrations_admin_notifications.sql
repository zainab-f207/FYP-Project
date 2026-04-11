-- Admin Notifications Table for SuperAdmin Dashboard
CREATE TABLE IF NOT EXISTS admin_notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    type VARCHAR(50) NOT NULL COMMENT 'Type: account_deleted, suspicious_activity, new_registration, system_alert',
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    data JSON COMMENT 'Additional data in JSON format',
    is_read BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    read_at DATETIME NULL,
    INDEX idx_type (type),
    INDEX idx_is_read (is_read),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
