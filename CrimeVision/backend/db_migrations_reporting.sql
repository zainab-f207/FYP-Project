-- Reporting System Database Migrations

-- Create reports table
CREATE TABLE IF NOT EXISTS reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'crime-summary', 'user-activity', 'system-health'
    format VARCHAR(20) NOT NULL, -- 'pdf', 'excel'
    file_path VARCHAR(500) NOT NULL,
    file_size INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'generating', 'completed', 'failed'
    created_by VARCHAR(50) NOT NULL,
    parameters JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_type (type),
    INDEX idx_status (status),
    INDEX idx_created_by (created_by),
    INDEX idx_created (created_at)
);

-- Create scheduled_reports table
CREATE TABLE IF NOT EXISTS scheduled_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'crime-summary', 'user-activity', 'system-health'
    schedule VARCHAR(50) NOT NULL, -- 'daily', 'weekly', 'monthly'
    format VARCHAR(20) NOT NULL, -- 'pdf', 'excel'
    recipients JSON, -- Array of email addresses
    parameters JSON,
    next_run TIMESTAMP NOT NULL,
    last_run TIMESTAMP NULL,
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'paused', 'cancelled'
    created_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_type (type),
    INDEX idx_schedule (schedule),
    INDEX idx_status (status),
    INDEX idx_next_run (next_run),
    INDEX idx_created_by (created_by)
);
