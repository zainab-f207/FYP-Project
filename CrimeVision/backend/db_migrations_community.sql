-- Community Features Database Migration
-- This migration adds tables for community safety features

-- Neighborhood Watch Groups table
CREATE TABLE IF NOT EXISTS neighborhood_watch_groups (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    area VARCHAR(255) NOT NULL,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    radius_km DECIMAL(5, 2) DEFAULT 2.0,
    max_members INT DEFAULT 50,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Group Members table
CREATE TABLE IF NOT EXISTS group_members (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id INT NOT NULL,
    user_id INT NOT NULL,
    role ENUM('member', 'moderator', 'admin') DEFAULT 'member',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (group_id) REFERENCES neighborhood_watch_groups(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_group_user (group_id, user_id)
);

-- Community Alerts table
CREATE TABLE IF NOT EXISTS community_alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    alert_type ENUM('emergency', 'warning', 'info', 'safety') DEFAULT 'info',
    severity ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium',
    area VARCHAR(255),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    radius_km DECIMAL(5, 2) DEFAULT 5.0,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE,
    view_count INT DEFAULT 0,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Alert Subscriptions table
CREATE TABLE IF NOT EXISTS alert_subscriptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    alert_type ENUM('emergency', 'warning', 'info', 'safety', 'all') DEFAULT 'all',
    area VARCHAR(255),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    radius_km DECIMAL(5, 2) DEFAULT 10.0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_alert_type (user_id, alert_type, area)
);

-- Safety Resources table
CREATE TABLE IF NOT EXISTS safety_resources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    resource_type ENUM('guide', 'protocol', 'training', 'toolkit', 'article') DEFAULT 'guide',
    category VARCHAR(100),
    content TEXT,
    file_path VARCHAR(500),
    file_size INT,
    mime_type VARCHAR(100),
    download_count INT DEFAULT 0,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_public BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Safety Network Connections table
CREATE TABLE IF NOT EXISTS safety_network_connections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    requester_id INT NOT NULL,
    target_id INT NOT NULL,
    connection_type ENUM('neighbor', 'authority', 'emergency_contact') DEFAULT 'neighbor',
    status ENUM('pending', 'accepted', 'declined', 'blocked') DEFAULT 'pending',
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    responded_at TIMESTAMP NULL,
    notes TEXT,
    FOREIGN KEY (requester_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_connection (requester_id, target_id)
);

-- Incident Reports table (for community incident reporting)
CREATE TABLE IF NOT EXISTS community_incident_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    incident_type VARCHAR(100),
    severity ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium',
    area VARCHAR(255),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    reported_by INT,
    assigned_group_id INT NULL,
    status ENUM('reported', 'investigating', 'resolved', 'closed') DEFAULT 'reported',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,
    is_anonymous BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (reported_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_group_id) REFERENCES neighborhood_watch_groups(id) ON DELETE SET NULL
);

-- Patrol Requests table
CREATE TABLE IF NOT EXISTS patrol_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    requested_by INT,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    urgency ENUM('low', 'medium', 'high') DEFAULT 'medium',
    description TEXT,
    status ENUM('pending', 'assigned', 'completed', 'cancelled') DEFAULT 'pending',
    assigned_to INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    responded_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    FOREIGN KEY (requested_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL
);

-- Community Activity Log table
CREATE TABLE IF NOT EXISTS community_activity_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    activity_type ENUM('joined_group', 'left_group', 'reported_incident', 'created_alert', 'downloaded_resource', 'made_connection', 'requested_patrol'),
    description TEXT,
    related_id INT NULL, -- ID of related record (group, alert, etc.)
    area VARCHAR(255),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Indexes for better performance
CREATE INDEX idx_neighborhood_watch_groups_area ON neighborhood_watch_groups(area);
CREATE INDEX idx_neighborhood_watch_groups_active ON neighborhood_watch_groups(is_active);
CREATE INDEX idx_group_members_group_id ON group_members(group_id);
CREATE INDEX idx_group_members_user_id ON group_members(user_id);
CREATE INDEX idx_community_alerts_area ON community_alerts(area);
CREATE INDEX idx_community_alerts_active ON community_alerts(is_active);
CREATE INDEX idx_community_alerts_created_at ON community_alerts(created_at);
CREATE INDEX idx_alert_subscriptions_user_id ON alert_subscriptions(user_id);
CREATE INDEX idx_safety_resources_type ON safety_resources(resource_type);
CREATE INDEX idx_safety_resources_active ON safety_resources(is_active);
CREATE INDEX idx_safety_network_connections_requester ON safety_network_connections(requester_id);
CREATE INDEX idx_safety_network_connections_target ON safety_network_connections(target_id);
CREATE INDEX idx_community_incident_reports_area ON community_incident_reports(area);
CREATE INDEX idx_community_incident_reports_status ON community_incident_reports(status);
CREATE INDEX idx_patrol_requests_status ON patrol_requests(status);
CREATE INDEX idx_community_activity_log_user ON community_activity_log(user_id);
CREATE INDEX idx_community_activity_log_type ON community_activity_log(activity_type);

-- Insert some sample safety resources
INSERT INTO safety_resources (title, description, resource_type, category, content, is_public) VALUES
('Emergency Response Guide', 'Comprehensive guide for handling emergency situations in your community', 'guide', 'Emergency Response', 'This guide covers immediate actions to take during various emergency situations including fire, medical emergencies, and security threats.', TRUE),
('Neighborhood Safety Protocols', 'Best practices for maintaining safe neighborhoods', 'protocol', 'Community Safety', 'Guidelines for community members to follow for maintaining safety in residential areas.', TRUE),
('Personal Safety Training', 'Interactive training module for personal safety awareness', 'training', 'Personal Safety', 'Comprehensive training covering personal safety, awareness, and prevention strategies.', TRUE),
('Community Safety Toolkit', 'Downloadable tools and checklists for safety planning', 'toolkit', 'Planning', 'Collection of checklists, forms, and planning tools for community safety initiatives.', TRUE);

-- Insert sample neighborhood watch groups
INSERT INTO neighborhood_watch_groups (name, description, area, latitude, longitude, max_members) VALUES
('Downtown Safety Watch', 'Active neighborhood watch group for downtown area', 'Downtown', 31.5204, 74.3587, 100),
('Residential Safety Network', 'Community safety network for residential neighborhoods', 'Residential Area', 31.5500, 74.3200, 75),
('Commercial District Watch', 'Safety monitoring for commercial and business districts', 'Commercial District', 31.5300, 74.3400, 50);
