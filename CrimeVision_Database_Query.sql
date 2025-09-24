use crimevision_db;
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'public') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE crimes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    crime_date DATE NOT NULL,
    area VARCHAR(100) NOT NULL,
    crime_type VARCHAR(100) NOT NULL,
    latitude DECIMAL(9,6) NOT NULL,
    longitude DECIMAL(9,6) NOT NULL,
    risk_level ENUM('Low', 'Medium', 'High') NOT NULL,
    source ENUM('admin', 'public', 'predicted') NOT NULL,
    status ENUM('verified', 'unverified') NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE areas (
    area_name VARCHAR(100) PRIMARY KEY,
    latitude DECIMAL(9,6) NOT NULL,
    longitude DECIMAL(9,6) NOT NULL
);

CREATE TABLE user_locations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    area VARCHAR(100) NOT NULL,
    latitude DECIMAL(9,6) NOT NULL,
    longitude DECIMAL(9,6) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);


