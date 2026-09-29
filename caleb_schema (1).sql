-- =====================================================================
-- CALEB — Camera Assisted License Entry Barrier
-- Database schema + sample data (MariaDB 10.5+)
-- Run with:  mariadb -u root -p < caleb_schema.sql
-- WARNING: drops and rebuilds the caleb database (fine for development)
-- =====================================================================

DROP DATABASE IF EXISTS caleb;
CREATE DATABASE caleb CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE caleb;

-- ---------------------------------------------------------------------
-- 1. parking_lots — one row per lot / physical gate on the model
-- ---------------------------------------------------------------------
CREATE TABLE parking_lots (
    lot_id       TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    lot_code     VARCHAR(10)  NOT NULL,          -- short label, e.g. 'A'
    lot_name     VARCHAR(50)  NOT NULL,
    gate_number  TINYINT UNSIGNED NOT NULL,      -- which gate the controller opens
    PRIMARY KEY (lot_id),
    UNIQUE KEY uq_lot_code (lot_code),
    UNIQUE KEY uq_gate_number (gate_number)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 2. vehicles — authorized (and deliberately unauthorized) plates
-- ---------------------------------------------------------------------
CREATE TABLE vehicles (
    vehicle_id    INT UNSIGNED NOT NULL AUTO_INCREMENT,
    plate_number  VARCHAR(10)  NOT NULL,
    authorized    BOOLEAN      NOT NULL DEFAULT TRUE,
    lot_id        TINYINT UNSIGNED NULL,          -- NULL = no lot assigned
    user_type     ENUM('student','faculty','staff','visitor') NOT NULL,
    owner_name    VARCHAR(80)  NULL,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (vehicle_id),
    UNIQUE KEY uq_plate (plate_number),
    CONSTRAINT chk_plate_format CHECK (plate_number REGEXP '^[A-Z0-9]{2,10}$'),
    CONSTRAINT fk_vehicle_lot FOREIGN KEY (lot_id)
        REFERENCES parking_lots (lot_id)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 3. access_log — every attempt, granted or denied, known or unknown
-- ---------------------------------------------------------------------
CREATE TABLE access_log (
    log_id        BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    event_time    DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    plate_read    VARCHAR(16)  NOT NULL,          -- exactly what OCR produced (normalized)
    confidence    DECIMAL(4,3) NULL,              -- 0.000 – 1.000
    result        ENUM('granted','denied') NOT NULL,
    deny_reason   ENUM('not_found','not_authorized','no_lot','low_confidence') NULL,
    lot_id        TINYINT UNSIGNED NULL,          -- lot granted at that moment
    PRIMARY KEY (log_id),
    KEY idx_event_time (event_time),
    KEY idx_plate_read (plate_read),
    CONSTRAINT chk_confidence CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    CONSTRAINT chk_result_reason CHECK (
        (result = 'granted' AND deny_reason IS NULL AND lot_id IS NOT NULL) OR
        (result = 'denied'  AND deny_reason IS NOT NULL)
    ),
    CONSTRAINT fk_log_lot FOREIGN KEY (lot_id)
        REFERENCES parking_lots (lot_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Sample data
-- ---------------------------------------------------------------------
INSERT INTO parking_lots (lot_code, lot_name, gate_number) VALUES
    ('A', 'Faculty/Staff Lot', 1),
    ('B', 'Student Lot',       2);

INSERT INTO vehicles (plate_number, authorized, lot_id, user_type, owner_name) VALUES
    ('ABC1234', TRUE,  1, 'faculty', 'Test Faculty'),
    ('TTU2026', TRUE,  2, 'student', 'Test Student'),
    ('RDR5678', TRUE,  2, 'student', 'Test Student 2'),
    ('STF9012', TRUE,  1, 'staff',   'Test Staff'),
    ('BAN0001', FALSE, 2, 'student', 'Revoked Permit'),     -- known but denied
    ('NOLOT01', TRUE,  NULL, 'visitor', 'Visitor, no lot');  -- authorized, no lot

-- ---------------------------------------------------------------------
-- Least-privilege account for the Python/camera code.
-- Change the password before real use. The '%' host lets it connect
-- from another machine; use 'localhost' if Python runs on the Pi itself.
-- ---------------------------------------------------------------------
CREATE USER IF NOT EXISTS 'caleb_app'@'localhost' IDENTIFIED BY 'change_me';
GRANT SELECT ON caleb.vehicles     TO 'caleb_app'@'localhost';
GRANT SELECT ON caleb.parking_lots TO 'caleb_app'@'localhost';
GRANT SELECT, INSERT ON caleb.access_log TO 'caleb_app'@'localhost';
FLUSH PRIVILEGES;
