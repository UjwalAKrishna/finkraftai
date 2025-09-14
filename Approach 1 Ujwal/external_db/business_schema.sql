-- Business Database Schema - Customer's actual business data
-- This represents a typical customer's database with real business entities

-- Companies/Vendors table
CREATE TABLE vendors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_code TEXT UNIQUE NOT NULL,
    vendor_name TEXT NOT NULL,
    contact_person TEXT,
    email TEXT,
    phone TEXT,
    address TEXT,
    gstin TEXT,
    status TEXT DEFAULT 'active', -- active, inactive, blocked
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Products/Services table
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT UNIQUE NOT NULL,
    product_name TEXT NOT NULL,
    category TEXT,
    unit_price DECIMAL(10,2),
    tax_rate DECIMAL(5,2) DEFAULT 18.00,
    status TEXT DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Invoices table - main business data
CREATE TABLE invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT UNIQUE NOT NULL,
    vendor_id INTEGER NOT NULL,
    invoice_date DATE NOT NULL,
    due_date DATE,
    total_amount DECIMAL(15,2) NOT NULL,
    tax_amount DECIMAL(15,2) DEFAULT 0,
    net_amount DECIMAL(15,2) NOT NULL,
    status TEXT DEFAULT 'pending', -- pending, processed, failed, cancelled
    payment_status TEXT DEFAULT 'unpaid', -- unpaid, partial, paid, overdue
    gstin_verified BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vendor_id) REFERENCES vendors(id)
);

-- Invoice line items
CREATE TABLE invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    product_id INTEGER,
    description TEXT NOT NULL,
    quantity DECIMAL(10,3) DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(15,2) NOT NULL,
    tax_amount DECIMAL(15,2) DEFAULT 0,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Sales/Revenue data
CREATE TABLE sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_date DATE NOT NULL,
    customer_name TEXT NOT NULL,
    product_id INTEGER,
    quantity DECIMAL(10,3),
    unit_price DECIMAL(10,2),
    total_amount DECIMAL(15,2) NOT NULL,
    region TEXT,
    salesperson TEXT,
    status TEXT DEFAULT 'completed',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Transactions/Payments
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT UNIQUE NOT NULL,
    invoice_id INTEGER,
    transaction_date DATE NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    payment_method TEXT, -- bank_transfer, credit_card, cash, cheque
    reference_number TEXT,
    status TEXT DEFAULT 'completed', -- pending, completed, failed, reversed
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);

-- Indexes for better performance
CREATE INDEX idx_invoices_vendor ON invoices(vendor_id);
CREATE INDEX idx_invoices_date ON invoices(invoice_date);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_sales_date ON sales(sale_date);
CREATE INDEX idx_transactions_date ON transactions(transaction_date);
CREATE INDEX idx_vendors_code ON vendors(vendor_code);