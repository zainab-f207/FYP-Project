-- Database migrations for reporting system

-- Create report_history table
CREATE TABLE IF NOT EXISTS report_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_type VARCHAR(50) NOT NULL,
    report_name VARCHAR(255) NOT NULL,
    format VARCHAR(10) NOT NULL DEFAULT 'pdf',
    generated_by VARCHAR(100) NOT NULL,
    generated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    file_path VARCHAR(500),
    file_size INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    filters JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_report_type (report_type),
    INDEX idx_generated_by (generated_by),
    INDEX idx_generated_at (generated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create scheduled_reports table
CREATE TABLE IF NOT EXISTS scheduled_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_type VARCHAR(50) NOT NULL,
    report_name VARCHAR(255) NOT NULL,
    schedule_frequency VARCHAR(20) NOT NULL,
    schedule_time TIME DEFAULT '09:00:00',
    recipients TEXT,
    format VARCHAR(10) NOT NULL DEFAULT 'pdf',
    is_active BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(100) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_run_at DATETIME,
    next_run_at DATETIME,
    filters JSON,
    INDEX idx_next_run (next_run_at),
    INDEX idx_is_active (is_active),
    INDEX idx_created_by (created_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
