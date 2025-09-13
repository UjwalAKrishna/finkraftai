# Business database sample data generator

import sqlite3
import random
from datetime import datetime, timedelta
from decimal import Decimal

def create_business_database(db_path: str = "business_data.db"):
    """Create and populate business database with realistic data"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Create schema
        with open("external_db/business_schema.sql", "r") as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)
        
        print("✓ Business database schema created")
        
        # Insert sample data
        insert_vendors(cursor)
        insert_products(cursor)
        insert_invoices(cursor)
        insert_sales(cursor)
        insert_transactions(cursor)
        
        conn.commit()
        print("✓ Business database populated with sample data")
        
        # Print summary
        print_data_summary(cursor)
        
    except Exception as e:
        print(f"Error creating business database: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def insert_vendors(cursor):
    """Insert sample vendors"""
    
    vendors = [
        ('INDIS001', 'IndiSky Airlines', 'Rajesh Kumar', 'rajesh@indisky.com', '+91-11-4567-8901', 'Delhi, India', '07AABCI1234M1Z5', 'active'),
        ('TECHS002', 'TechSolutions Pvt Ltd', 'Priya Sharma', 'priya@techsol.com', '+91-80-2345-6789', 'Bangalore, India', '29AABCT1234M1Z5', 'active'),
        ('GLOBA003', 'Global Imports LLC', 'John Smith', 'john@globalimports.com', '+1-555-123-4567', 'New York, USA', '', 'active'),
        ('AUTOM004', 'AutoMotive Parts Co', 'Maria Garcia', 'maria@autoparts.com', '+1-555-987-6543', 'Detroit, USA', '', 'active'),
        ('FOODS005', 'FoodSupply Chain Ltd', 'Ahmed Hassan', 'ahmed@foodchain.com', '+971-4-123-4567', 'Dubai, UAE', '', 'active'),
        ('STEEL006', 'Steel Industries Inc', 'David Wilson', 'david@steelinc.com', '+1-555-456-7890', 'Pittsburgh, USA', '', 'blocked'),
        ('ELECT007', 'Electronics Hub', 'Li Wei', 'li.wei@electrohub.cn', '+86-21-8765-4321', 'Shanghai, China', '', 'active'),
        ('TEXTL008', 'Textile Mills Ltd', 'Fatima Khan', 'fatima@textmills.pk', '+92-21-9876-5432', 'Karachi, Pakistan', '27AABCT5678N1Z5', 'inactive'),
        ('PHARM009', 'Pharma Solutions', 'Dr. Sarah Brown', 'sarah@pharmasol.com', '+44-20-7890-1234', 'London, UK', '', 'active'),
        ('ENERG010', 'Energy Systems Corp', 'Michael Johnson', 'mike@energysys.com', '+1-555-345-6789', 'Houston, USA', '', 'active'),
    ]
    
    cursor.executemany(
        "INSERT INTO vendors (vendor_code, vendor_name, contact_person, email, phone, address, gstin, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        vendors
    )

def insert_products(cursor):
    """Insert sample products"""
    
    products = [
        ('FLIGHT001', 'Domestic Flight Booking', 'Travel', 5000.00, 12.00),
        ('SOFTWARE001', 'Software License', 'Technology', 25000.00, 18.00),
        ('HARDWARE001', 'Computer Hardware', 'Technology', 75000.00, 18.00),
        ('AUTOPART001', 'Engine Components', 'Automotive', 15000.00, 18.00),
        ('FOOD001', 'Food Supplies', 'FMCG', 500.00, 5.00),
        ('STEEL001', 'Steel Sheets', 'Raw Material', 50000.00, 18.00),
        ('ELECTRONIC001', 'Electronic Components', 'Electronics', 8000.00, 18.00),
        ('TEXTILE001', 'Cotton Fabric', 'Textile', 1200.00, 12.00),
        ('MEDICINE001', 'Pharmaceutical Products', 'Healthcare', 3000.00, 5.00),
        ('ENERGY001', 'Solar Panels', 'Energy', 45000.00, 18.00),
    ]
    
    cursor.executemany(
        "INSERT INTO products (product_code, product_name, category, unit_price, tax_rate) VALUES (?, ?, ?, ?, ?)",
        products
    )

def insert_invoices(cursor):
    """Insert realistic invoice data including the failed IndiSky invoices"""
    
    # Get vendor and product IDs
    cursor.execute("SELECT id, vendor_code FROM vendors")
    vendor_map = {code: id for id, code in cursor.fetchall()}
    
    cursor.execute("SELECT id FROM products")
    product_ids = [row[0] for row in cursor.fetchall()]
    
    invoices = []
    
    # Generate invoices for the last 3 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    invoice_num = 1000
    
    for vendor_code, vendor_id in vendor_map.items():
        # Generate 10-15 invoices per vendor
        num_invoices = random.randint(8, 15)
        
        for _ in range(num_invoices):
            invoice_date = start_date + timedelta(days=random.randint(0, 90))
            due_date = invoice_date + timedelta(days=30)
            
            # Determine status - make IndiSky have more failed invoices for the sample scenario
            if vendor_code == 'INDIS001':  # IndiSky
                # 70% failed for IndiSky (sample scenario)
                status = 'failed' if random.random() < 0.7 else random.choice(['pending', 'processed'])
                gstin_verified = False if status == 'failed' else True
                error_msg = "Missing GSTIN information" if status == 'failed' else None
            else:
                # Other vendors have normal distribution
                status = random.choices(['processed', 'pending', 'failed'], weights=[70, 20, 10])[0]
                gstin_verified = status != 'failed'
                error_msg = random.choice([
                    "Missing GSTIN information", 
                    "Invalid invoice format", 
                    "Amount mismatch"
                ]) if status == 'failed' else None
            
            total_amount = round(random.uniform(5000, 100000), 2)
            tax_amount = round(total_amount * 0.18, 2)
            net_amount = total_amount + tax_amount
            
            payment_status = 'paid' if status == 'processed' else random.choice(['unpaid', 'partial', 'overdue'])
            
            invoices.append((
                f"INV-{invoice_num:06d}",
                vendor_id,
                invoice_date.strftime('%Y-%m-%d'),
                due_date.strftime('%Y-%m-%d'),
                total_amount,
                tax_amount,
                net_amount,
                status,
                payment_status,
                gstin_verified,
                error_msg
            ))
            
            invoice_num += 1
    
    cursor.executemany("""
        INSERT INTO invoices (invoice_number, vendor_id, invoice_date, due_date, 
                            total_amount, tax_amount, net_amount, status, payment_status, 
                            gstin_verified, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, invoices)

def insert_sales(cursor):
    """Insert sample sales data"""
    
    cursor.execute("SELECT id FROM products")
    product_ids = [row[0] for row in cursor.fetchall()]
    
    sales = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    customers = [
        'ABC Corp', 'XYZ Ltd', 'TechStart Inc', 'Global Enterprises', 'Local Business',
        'Innovation Labs', 'Future Tech', 'Smart Solutions', 'Digital World', 'Modern Corp'
    ]
    
    regions = ['North', 'South', 'East', 'West', 'Central']
    salespeople = ['Amit Kumar', 'Priya Singh', 'Rohit Sharma', 'Sneha Patel', 'Rajesh Gupta']
    
    for _ in range(500):  # 500 sales records
        sale_date = start_date + timedelta(days=random.randint(0, 90))
        customer = random.choice(customers)
        product_id = random.choice(product_ids)
        quantity = round(random.uniform(1, 20), 2)
        unit_price = round(random.uniform(100, 10000), 2)
        total_amount = round(quantity * unit_price, 2)
        
        sales.append((
            sale_date.strftime('%Y-%m-%d'),
            customer,
            product_id,
            quantity,
            unit_price,
            total_amount,
            random.choice(regions),
            random.choice(salespeople),
            'completed'
        ))
    
    cursor.executemany("""
        INSERT INTO sales (sale_date, customer_name, product_id, quantity, 
                         unit_price, total_amount, region, salesperson, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, sales)

def insert_transactions(cursor):
    """Insert sample transaction data"""
    
    # Get processed invoices
    cursor.execute("SELECT id, net_amount FROM invoices WHERE status = 'processed'")
    processed_invoices = cursor.fetchall()
    
    transactions = []
    txn_id = 10000
    
    payment_methods = ['bank_transfer', 'credit_card', 'cheque', 'cash']
    
    for invoice_id, amount in processed_invoices:
        # Most processed invoices have payments
        if random.random() < 0.9:
            txn_date = datetime.now() - timedelta(days=random.randint(1, 30))
            
            transactions.append((
                f"TXN-{txn_id:08d}",
                invoice_id,
                txn_date.strftime('%Y-%m-%d'),
                amount,
                random.choice(payment_methods),
                f"REF-{txn_id}",
                'completed'
            ))
            
            txn_id += 1
    
    cursor.executemany("""
        INSERT INTO transactions (transaction_id, invoice_id, transaction_date, 
                                amount, payment_method, reference_number, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, transactions)

def print_data_summary(cursor):
    """Print summary of generated data"""
    
    print("\n=== Business Database Summary ===")
    
    # Vendors
    cursor.execute("SELECT COUNT(*) FROM vendors")
    print(f"Vendors: {cursor.fetchone()[0]}")
    
    # Products
    cursor.execute("SELECT COUNT(*) FROM products")
    print(f"Products: {cursor.fetchone()[0]}")
    
    # Invoices by status
    cursor.execute("SELECT status, COUNT(*) FROM invoices GROUP BY status")
    print("Invoices by status:")
    for status, count in cursor.fetchall():
        print(f"  {status}: {count}")
    
    # IndiSky specific data (for sample scenario)
    cursor.execute("""
        SELECT COUNT(*) FROM invoices i 
        JOIN vendors v ON i.vendor_id = v.id 
        WHERE v.vendor_code = 'INDIS001' AND i.status = 'failed'
    """)
    indisky_failed = cursor.fetchone()[0]
    print(f"IndiSky failed invoices: {indisky_failed}")
    
    # Sales
    cursor.execute("SELECT COUNT(*) FROM sales")
    print(f"Sales records: {cursor.fetchone()[0]}")
    
    # Transactions
    cursor.execute("SELECT COUNT(*) FROM transactions")
    print(f"Transactions: {cursor.fetchone()[0]}")

if __name__ == "__main__":
    create_business_database()