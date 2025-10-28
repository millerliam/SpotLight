DROP DATABASE IF EXISTS `SpotLight`;
CREATE DATABASE `SpotLight`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE `SpotLight`;

CREATE TABLE IF NOT EXISTS Employee (
  eID INT AUTO_INCREMENT PRIMARY KEY,
  lName VARCHAR(50),
  fNAME VARCHAR(50),
  email VARCHAR(50),
  Avatar_URL VARCHAR(100),
  role ENUM('sales','o&m') NOT NULL
);

CREATE TABLE IF NOT EXISTS Customers (
  cID INT AUTO_INCREMENT PRIMARY KEY,
  fName VARCHAR(50),
  lName VARCHAR(50),
  email VARCHAR(50),
  position VARCHAR(50),
  companyName VARCHAR(50),
  totalOrderTimes INT,
  VIP BOOL,
  avatarURL VARCHAR(100),
  balance DECIMAL(10,2),
  TEL VARCHAR(20),
  updated_by_eID INT NULL,
  updated_at TIMESTAMP NULL,
  FOREIGN KEY (updated_by_eID) REFERENCES Employee(eID)
    ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS Spot (
  spotID INT AUTO_INCREMENT PRIMARY KEY,
  price DECIMAL(10,2),
  contactTel VARCHAR(20),
  imageURL VARCHAR(100),
  estViewPerMonth INT,
  monthlyRentCost DECIMAL(10,2),
  status ENUM('free', 'inuse', 'w.issue', 'planned'),
  endTimeOfCurrentOrder DATE,
  address VARCHAR(100),
  latitude DOUBLE,
  longitude DOUBLE,
  FULLTEXT KEY ft_address (address),
  updated_by_eID INT NULL,
  updated_at TIMESTAMP NULL,
  FOREIGN KEY (updated_by_eID) REFERENCES Employee(eID)
    ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS Reviews (
  rID INT AUTO_INCREMENT PRIMARY KEY,
  spotID INT,
  review TEXT,
  rating INT,
  cID INT,
  lastUpdate TIMESTAMP,
  is_deleted TINYINT(1) NOT NULL DEFAULT 0,
  CONSTRAINT chk_ratingrange CHECK (rating >= 0 AND rating <= 5),
  FOREIGN KEY (spotID) REFERENCES Spot(spotID) ON UPDATE CASCADE ON DELETE RESTRICT,
  FOREIGN KEY (cID)   REFERENCES Customers(cID) ON UPDATE CASCADE ON DELETE RESTRICT,
  updated_by_eID INT NULL,
  updated_at TIMESTAMP NULL,
  FOREIGN KEY (updated_by_eID) REFERENCES Employee(eID)
    ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS Orders (
  orderID INT AUTO_INCREMENT PRIMARY KEY,
  `date` DATE,
  total DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  cID INT NOT NULL,
  status ENUM('pending','active','scheduled','fulfilled','canceled') NOT NULL DEFAULT 'pending',
  placed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  processed_at DATETIME NULL,
  processed_by_eID INT NULL,
  updated_by_eID INT NULL,
  updated_at TIMESTAMP NULL,
  CONSTRAINT chk_totalnotnegative CHECK (total >= 0),
  FOREIGN KEY (cID) REFERENCES Customers(cID) ON UPDATE CASCADE ON DELETE RESTRICT,
  FOREIGN KEY (processed_by_eID) REFERENCES Employee(eID) ON UPDATE CASCADE ON DELETE SET NULL,
  FOREIGN KEY (updated_by_eID)   REFERENCES Employee(eID) ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS SpotOrder (
  orderID INT NOT NULL,
  spotID  INT NOT NULL,
  spot_cost DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  lease_start_date DATE NOT NULL,
  lease_end_date   DATE NOT NULL,
  updated_by_eID INT NULL,
  updated_at TIMESTAMP NULL,
  PRIMARY KEY (orderID, spotID),
  CONSTRAINT chk_spotorder_dates CHECK (lease_start_date <= lease_end_date),
  FOREIGN KEY (orderID) REFERENCES Orders(orderID) ON UPDATE CASCADE ON DELETE CASCADE,
  FOREIGN KEY (spotID)  REFERENCES Spot(spotID)   ON UPDATE CASCADE ON DELETE RESTRICT,
  FOREIGN KEY (updated_by_eID) REFERENCES Employee(eID)
    ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE INDEX idx_orders_cid       ON Orders(cID);
CREATE INDEX idx_orders_processed ON Orders(processed_at);
CREATE INDEX idx_spotorder_order  ON SpotOrder(orderID);
CREATE INDEX idx_spotorder_spot   ON SpotOrder(spotID);
CREATE INDEX idx_spot_dates       ON SpotOrder(spotID, lease_start_date, lease_end_date);
CREATE INDEX idx_reviews_spot     ON Reviews(spotID);
CREATE INDEX idx_reviews_cid      ON Reviews(cID);
