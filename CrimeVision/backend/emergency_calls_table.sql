-- Emergency Calls Table Schema
CREATE TABLE IF NOT EXISTS emergency_calls (
    id INT AUTO_INCREMENT PRIMARY KEY,
    contact_name VARCHAR(100) NOT NULL,
    contact_number VARCHAR(20) NOT NULL,
    caller_location_lat DECIMAL(10, 8),
    caller_location_lng DECIMAL(11, 8),
    caller_address VARCHAR(255),
    call_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INT NULL,
    username VARCHAR(50),
    emergency_type VARCHAR(50) DEFAULT 'general',
    status VARCHAR(20) DEFAULT 'completed',
    FOREIGN KEY (user_id) REFERENCES users_info(id) ON DELETE SET NULL,
    INDEX idx_calls_timestamp (call_timestamp),
    INDEX idx_calls_user (user_id),
    INDEX idx_calls_type (emergency_type)
);
