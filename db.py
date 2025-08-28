import sqlite3
from datetime import datetime
import os

DATABASE_NAME = 'inventory.db'


def init_db():
    """Inicializa la base de datos con las tablas necesarias"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    # Tabla de productos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            precio_venta REAL NOT NULL DEFAULT 0,
            precio_proveedor REAL NOT NULL DEFAULT 0,
            cantidad INTEGER NOT NULL DEFAULT 0,
            ubicacion TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabla de facturas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS facturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_factura TEXT UNIQUE NOT NULL,
            cliente_nombre TEXT NOT NULL,
            cliente_contacto TEXT,
            cliente_email TEXT,
            subtotal REAL NOT NULL,
            iva REAL NOT NULL,
            total REAL NOT NULL,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabla de items de factura
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS factura_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            factura_id INTEGER NOT NULL,
            producto_id INTEGER NOT NULL,
            cantidad INTEGER NOT NULL,
            precio_unitario REAL NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (factura_id) REFERENCES facturas (id),
            FOREIGN KEY (producto_id) REFERENCES productos (id)
        )
    ''')

    conn.commit()
    conn.close()


def get_db_connection():
    """Obtiene una conexión a la base de datos"""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


class ProductoDB:
    @staticmethod
    def agregar_producto(nombre, descripcion='', precio_venta=0, precio_proveedor=0, cantidad=0, ubicacion=''):
        """Agrega un nuevo producto al inventario"""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO productos (nombre, descripcion, precio_venta, precio_proveedor, cantidad, ubicacion)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (nombre, descripcion, precio_venta, precio_proveedor, cantidad, ubicacion))

        producto_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return producto_id

    @staticmethod
    def buscar_productos(termino):
        """Busca productos por nombre o descripción"""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM productos 
            WHERE nombre LIKE ? OR descripcion LIKE ?
            ORDER BY nombre
        ''', (f'%{termino}%', f'%{termino}%'))

        productos = cursor.fetchall()
        conn.close()
        return [dict(producto) for producto in productos]

    @staticmethod
    def obtener_producto_por_id(producto_id):
        """Obtiene un producto por su ID"""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM productos WHERE id = ?', (producto_id,))
        producto = cursor.fetchone()
        conn.close()

        return dict(producto) if producto else None

    @staticmethod
    def actualizar_producto(producto_id, **kwargs):
        """Actualiza un producto existente"""
        conn = get_db_connection()
        cursor = conn.cursor()

        campos = []
        valores = []

        for campo, valor in kwargs.items():
            if campo in ['nombre', 'descripcion', 'precio_venta', 'precio_proveedor', 'cantidad', 'ubicacion']:
                campos.append(f'{campo} = ?')
                valores.append(valor)

        if not campos:
            conn.close()
            return False

        valores.append(producto_id)
        query = f'UPDATE productos SET {", ".join(campos)} WHERE id = ?'

        cursor.execute(query, valores)
        afectadas = cursor.rowcount
        conn.commit()
        conn.close()

        return afectadas > 0

    @staticmethod
    def obtener_todos_productos():
        """Obtiene todos los productos"""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM productos ORDER BY nombre')
        productos = cursor.fetchall()
        conn.close()

        return [dict(producto) for producto in productos]

    @staticmethod
    def reducir_stock(producto_id, cantidad):
        """Reduce el stock de un producto"""
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener cantidad actual
        cursor.execute('SELECT cantidad FROM productos WHERE id = ?', (producto_id,))
        resultado = cursor.fetchone()

        if not resultado:
            conn.close()
            return False, "Producto no encontrado"

        cantidad_actual = resultado['cantidad']

        if cantidad_actual < cantidad:
            conn.close()
            return False, "Stock insuficiente"

        # Actualizar cantidad
        nueva_cantidad = cantidad_actual - cantidad
        cursor.execute('UPDATE productos SET cantidad = ? WHERE id = ?', (nueva_cantidad, producto_id))

        conn.commit()
        conn.close()
        return True, "Stock actualizado"


class FacturaDB:
    @staticmethod
    def generar_numero_factura():
        """Genera un número de factura único"""
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener el último número de factura
        cursor.execute('SELECT MAX(id) as max_id FROM facturas')
        resultado = cursor.fetchone()

        max_id = resultado['max_id'] or 0
        numero = f"F{max_id + 1:06d}"

        conn.close()
        return numero

    @staticmethod
    def crear_factura(cliente_nombre, cliente_contacto='', cliente_email='', items=[]):
        """Crea una nueva factura"""
        conn = get_db_connection()
        cursor = conn.cursor()

        numero_factura = FacturaDB.generar_numero_factura()
        subtotal = 0

        # Calcular subtotal
        for item in items:
            subtotal += item['cantidad'] * item['precio_unitario']

        iva = subtotal * 0.19  # IVA del 19%
        total = subtotal + iva

        # Crear factura
        cursor.execute('''
            INSERT INTO facturas (numero_factura, cliente_nombre, cliente_contacto, cliente_email, subtotal, iva, total)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (numero_factura, cliente_nombre, cliente_contacto, cliente_email, subtotal, iva, total))

        factura_id = cursor.lastrowid

        # Agregar items de la factura
        for item in items:
            cursor.execute('''
                INSERT INTO factura_items (factura_id, producto_id, cantidad, precio_unitario, subtotal)
                VALUES (?, ?, ?, ?, ?)
            ''', (factura_id, item['producto_id'], item['cantidad'], item['precio_unitario'],
                  item['cantidad'] * item['precio_unitario']))

            # Reducir stock
            ProductoDB.reducir_stock(item['producto_id'], item['cantidad'])

        conn.commit()
        conn.close()

        return {
            'id': factura_id,
            'numero_factura': numero_factura,
            'subtotal': subtotal,
            'iva': iva,
            'total': total
        }

    @staticmethod
    def obtener_factura_completa(factura_id):
        """Obtiene una factura completa con sus items"""
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener datos de la factura
        cursor.execute('SELECT * FROM facturas WHERE id = ?', (factura_id,))
        factura = cursor.fetchone()

        if not factura:
            conn.close()
            return None

        # Obtener items de la factura
        cursor.execute('''
            SELECT fi.*, p.nombre as producto_nombre, p.descripcion as producto_descripcion
            FROM factura_items fi
            JOIN productos p ON fi.producto_id = p.id
            WHERE fi.factura_id = ?
        ''', (factura_id,))

        items = cursor.fetchall()
        conn.close()

        return {
            'factura': dict(factura),
            'items': [dict(item) for item in items]
        }

    @staticmethod
    def obtener_todas_facturas():
        """Obtiene todas las facturas"""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM facturas ORDER BY fecha_creacion DESC')
        facturas = cursor.fetchall()
        conn.close()

        return [dict(factura) for factura in facturas]


# Inicializar la base de datos al importar el módulo
if __name__ == "__main__":
    init_db()
    print("Base de datos inicializada correctamente")