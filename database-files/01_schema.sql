DROP DATABASE IF EXISTS `SpotLight`;
CREATE DATABASE `SpotLight`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE `SpotLight`;

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
  balance INT,
  TEL VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS Spot (
  spotID INT AUTO_INCREMENT PRIMARY KEY,
  price INT,
  contactTel VARCHAR(20),
  imageURL VARCHAR(100),
  estViewPerMonth INT,
  monthlyRentCost INT,
  endTimeOfCurrentOrder DATE,
  status ENUM('free', 'inuse', 'w.issue', 'planned'),
  address VARCHAR(100),
  latitude DOUBLE,
  longitude DOUBLE,
  FULLTEXT KEY ft_address (address)
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
  FOREIGN KEY (cID) REFERENCES Customers(cID) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS Employee (
  eID INT AUTO_INCREMENT PRIMARY KEY,
  lName VARCHAR(50),
  fNAME VARCHAR(50),
  position VARCHAR(50),
  email VARCHAR(50),
  Avatar_URL VARCHAR(100),
  Field VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS SalesMan (
  eID INT PRIMARY KEY,
  FOREIGN KEY (eID) REFERENCES Employee(eID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS OandM (
  eID INT PRIMARY KEY,
  FOREIGN KEY (eID) REFERENCES Employee(eID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Orders (
  orderID INT AUTO_INCREMENT PRIMARY KEY,
  date DATE,
  total INT,
  cID INT,
  status ENUM('pending','confirmed','active','fulfilled','canceled') DEFAULT 'pending',  
  CONSTRAINT chk_totalnotnegative CHECK (total >= 0),
  FOREIGN KEY (cID) REFERENCES Customers(cID) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS ToBeProcessedOrder (
  orderID INT PRIMARY KEY,
  status ENUM('in_chart', 'sent_as_order'),
  FOREIGN KEY (orderID) REFERENCES Orders(orderID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ProcessedOrder (
  orderID INT PRIMARY KEY,
  processTime TIMESTAMP,
  processorID INT,
  FOREIGN KEY (orderID) REFERENCES Orders(orderID) ON DELETE CASCADE,
  FOREIGN KEY (processorID) REFERENCES SalesMan(eID) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS SpotOrder (
  spotID INT,
  orderID INT,
  spot_cost DECIMAL(10,2) NOT NULL DEFAULT 0.00,  
  lease_start_date DATE,                           
  lease_end_date DATE,                            
  FOREIGN KEY (spotID) REFERENCES Spot(spotID) ON DELETE CASCADE,
  FOREIGN KEY (orderID) REFERENCES Orders(orderID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Report (
  rID INT AUTO_INCREMENT PRIMARY KEY,
  time TIMESTAMP,
  date DATE,
  status ENUM('unexamined', 'examined'),
  generatorID INT,
  examinerID INT,
  FOREIGN KEY (generatorID) REFERENCES SalesMan(eID) ON UPDATE CASCADE ON DELETE RESTRICT,
  FOREIGN KEY (examinerID) REFERENCES OandM(eID) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS InvalidSpotReport (
  rID INT PRIMARY KEY,
  orderID INT,
  FOREIGN KEY (rID) REFERENCES Report(rID) ON DELETE CASCADE,
  FOREIGN KEY (orderID) REFERENCES Orders(orderID) ON UPDATE CASCADE ON DELETE CASCADE
);
