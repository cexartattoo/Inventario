import sqlite3
import os
from datetime import datetime

DATABASE_PATH = 'inventory.db'


def init_db():
    """Inicializa la base de datos y crea las tablas necesarias"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Tabla de productos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference_number INTEGER UNIQUE,
            name TEXT NOT NULL,
            description TEXT,
            sale_price REAL,
            supplier_price REAL,
            quantity INTEGER DEFAULT 0,
            physical_location TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabla de facturas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT UNIQUE,
            customer_name TEXT NOT NULL,
            customer_phone TEXT,
            customer_email TEXT,
            subtotal REAL,
            tax_amount REAL,
            total_amount REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabla de items de factura
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER,
            product_id INTEGER,
            product_name TEXT,
            quantity INTEGER,
            unit_price REAL,
            total_price REAL,
            FOREIGN KEY (invoice_id) REFERENCES invoices (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')

    conn.commit()
    conn.close()


def get_connection():
    """Obtiene una conexión a la base de datos"""
    return sqlite3.connect(DATABASE_PATH)


def get_next_reference_number():
    """Obtiene el próximo número de referencia para un producto"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT MAX(reference_number) FROM products')
    result = cursor.fetchone()

    conn.close()

    if result[0] is None:
        return 1
    return result[0] + 1


def get_next_invoice_number():
    """Genera el próximo número de factura"""
    conn = get_connection()
    cursor = conn.cursor()

    today = datetime.now().strftime('%Y%m%d')
    cursor.execute('''
        SELECT COUNT(*) FROM invoices 
        WHERE DATE(created_at) = DATE('now')
    ''')

    daily_count = cursor.fetchone()[0] + 1
    conn.close()

    return f"FAC-{today}-{daily_count:03d}"


# Inicializar la base de datos al importar el módulo
if __name__ == "__main__":
    init_db()
    print("Base de datos inicializada correctamente")