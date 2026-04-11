-- ============================================================
-- PPC Law Sections Management - Database Migration
-- Moves hardcoded PPC/ATA/CNSA/etc. sections into database
-- with AI (Gemini) verification support
-- ============================================================

CREATE TABLE IF NOT EXISTS law_sections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    law_type VARCHAR(20) NOT NULL DEFAULT 'PPC',
    section_number VARCHAR(30) NOT NULL,
    english_title VARCHAR(500) NOT NULL,
    chapter VARCHAR(200) DEFAULT NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'hardcoded_initial',
    verified_by VARCHAR(100) DEFAULT NULL,
    verified_at DATETIME DEFAULT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    ai_response TEXT DEFAULT NULL,
    ai_model VARCHAR(50) DEFAULT NULL,
    last_ai_check DATETIME DEFAULT NULL,
    notes TEXT DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_law_section (law_type, section_number),
    INDEX idx_law_type (law_type),
    INDEX idx_verified (is_verified),
    INDEX idx_section_number (section_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Audit trail for changes
CREATE TABLE IF NOT EXISTS law_sections_audit (
    id INT AUTO_INCREMENT PRIMARY KEY,
    law_section_id INT NOT NULL,
    action VARCHAR(20) NOT NULL,
    old_title VARCHAR(500) DEFAULT NULL,
    new_title VARCHAR(500) DEFAULT NULL,
    changed_by VARCHAR(100) NOT NULL,
    change_reason TEXT DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_section_id (law_section_id),
    INDEX idx_changed_by (changed_by),
    FOREIGN KEY (law_section_id) REFERENCES law_sections(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

