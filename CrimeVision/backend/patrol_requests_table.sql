-- Patrol Requests Table Schema
CREATE TABLE IF NOT EXISTS patrol_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    username VARCHAR(50),
    request_type VARCHAR(50) DEFAULT 'general_patrol',
    location_lat DECIMAL(10, 8),
    location_lng DECIMAL(11, 8),
    address VARCHAR(255),
    request_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',
    urgency VARCHAR(20) DEFAULT 'medium',
    description TEXT,
    assigned_unit VARCHAR(100) NULL,
    response_timestamp TIMESTAMP NULL,
    completion_timestamp TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users_info(id) ON DELETE SET NULL,
    INDEX idx_patrol_timestamp (request_timestamp),
    INDEX idx_patrol_user (user_id),
    INDEX idx_patrol_status (status),
    INDEX idx_patrol_type (request_type)
);
