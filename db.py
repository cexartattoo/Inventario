import sqlite3
import os

DATABASE_FILE = 'inventory.db'


def get_db_connection():
    """
    Crea y retorna una conexión a la base de datos.
    La conexión está configurada para devolver filas como diccionarios y se asegura de que el archivo exista.
    """
    # La base de datos ahora se crea al inicio de la app, no aquí.
    # Esto evita el error de 'archivo en uso'.
    conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    """
    Crea las tablas necesarias en la base de datos si no existen.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tabla de productos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            sale_price REAL NOT NULL,
            supplier_price REAL,
            quantity INTEGER NOT NULL,
            location TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabla de facturas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            client_contact TEXT,
            client_email TEXT,
            subtotal REAL NOT NULL,
            tax REAL NOT NULL,
            total REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabla de ítems de la factura (relación muchos a muchos)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            FOREIGN KEY (invoice_id) REFERENCES invoices (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')

    conn.commit()
    conn.close()
    print("Tablas verificadas/creadas exitosamente.")


def init_db_with_examples():
    """
    Puebla la base de datos con datos de ejemplo si está vacía.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Verificar si ya hay productos para no insertar duplicados
    cursor.execute("SELECT COUNT(id) FROM products")
    count = cursor.fetchone()[0]

    if count == 0:
        print("La base de datos está vacía. Insertando datos de ejemplo...")
        products_data = [
            ('Tornillo M5 Acero Inoxidable', 'Tornillo de cabeza hexagonal M5x20mm', 0.5, 0.2, 500,
             'Estante A, Fila 1, Columna 1'),
            ('Tuerca M5 Zincada', 'Tuerca hexagonal para tornillo M5', 0.2, 0.08, 800, 'Estante A, Fila 1, Columna 2'),
            ('Arandela Plana M5', 'Arandela de presión para tornillo M5', 0.1, 0.04, 1200,
             'Estante A, Fila 1, Columna 3'),
            ('Llave Allen 4mm', 'Llave hexagonal para tornillos M5', 3.0, 1.5, 50, 'Cajón Herramientas 1'),
            ('Aceite Multiusos WD-40', 'Lata de aceite lubricante 8oz', 8.5, 5.0, 30, 'Estante B, Fila 2')
        ]

        cursor.executemany('''
            INSERT INTO products (name, description, sale_price, supplier_price, quantity, location)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', products_data)

        conn.commit()
        print(f"{cursor.rowcount} productos de ejemplo insertados.")
    else:
        print("La base de datos ya contiene datos.")

    conn.close()

