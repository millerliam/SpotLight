CREATE TABLE IF NOT EXISTS Employee (
  eID INT AUTO_INCREMENT PRIMARY KEY,
  lName VARCHAR(50),
  fNAME VARCHAR(50),
  position VARCHAR(50),
  email VARCHAR(50),
  Avatar_URL VARCHAR(100),
  Field VARCHAR(50),
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
  balance INT,
  TEL VARCHAR(20),
  updated_by_eID INT NULL,                    
  updated_at TIMESTAMP NULL,
  FOREIGN KEY (updated_by_eID) REFERENCES Employee(eID)
    ON UPDATE CASCADE ON DELETE SET NULL
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
  total INT NOT NULL,
  cID INT NOT NULL,
  status ENUM('pending','active','scheduled','fulfilled','canceled') NOT NULL DEFAULT 'pending',
  placed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  processed_at DATETIME NULL,
  processed_by_eID INT NULL,
  updated_by_eID INT NULL,
  updated_at TIMESTAMP NULL,
  CONSTRAINT chk_totalnotnegative CHECK (total >= 0),
  CONSTRAINT fk_orders_customer FOREIGN KEY (cID) REFERENCES Customers(cID) ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_orders_processed_by FOREIGN KEY (processed_by_eID) REFERENCES Employee(eID) ON UPDATE CASCADE ON DELETE SET NULL,
  CONSTRAINT fk_orders_updated_by FOREIGN KEY (updated_by_eID) REFERENCES Employee(eID) ON UPDATE CASCADE ON DELETE SET NULL
);


CREATE TABLE IF NOT EXISTS SpotOrder (
  spotID INT,
  orderID INT,
  spot_cost DECIMAL(10,2) NOT NULL DEFAULT 0.00,  
  lease_start_date DATE,                          
  lease_end_date DATE,                            
  FOREIGN KEY (spotID) REFERENCES Spot(spotID) ON DELETE CASCADE,
  FOREIGN KEY (orderID) REFERENCES Orders(orderID) ON DELETE CASCADE,
  updated_by_eID INT NULL,                         
  updated_at TIMESTAMP NULL,
  FOREIGN KEY (updated_by_eID) REFERENCES Employee(eID)
    ON UPDATE CASCADE ON DELETE SET NULL
);
