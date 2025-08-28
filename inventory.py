from fuzzywuzzy import process

SIMILARITY_THRESHOLD = 95


def find_product_by_name(conn, name):
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM products')
    all_products = cursor.fetchall()

    if not all_products:
        return None

    product_names = {prod['name']: prod['id'] for prod in all_products}
    best_match, score = process.extractOne(name, product_names.keys())

    if score >= SIMILARITY_THRESHOLD:
        product_id = product_names[best_match]
        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        product = cursor.fetchone()
        return dict(product) if product else None

    return None


def add_product(conn, name, description, sale_price, supplier_price, quantity, location):
    existing_product = find_product_by_name(conn, name)
    if existing_product:
        return {
            "status": "exists",
            "message": f"Ya existe un producto llamado '{existing_product['name']}'.",
            "product_id": existing_product['id']
        }

    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO products (name, description, sale_price, supplier_price, quantity, location)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, description, sale_price, supplier_price, quantity, location))
    conn.commit()
    new_id = cursor.lastrowid

    return {
        "status": "success",
        "message": f"Producto '{name}' agregado exitosamente.",
        "product_id": new_id
    }


def delete_product(conn, product_id):
    """
    Elimina un producto de la base de datos por su ID.
    """
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()

    if cursor.rowcount > 0:
        return {"status": "success", "message": "Producto eliminado exitosamente."}
    else:
        return {"status": "error", "message": "No se encontró el producto para eliminar."}


def update_stock(conn, product_id, quantity_change):
    cursor = conn.cursor()
    cursor.execute('SELECT quantity FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()

    if not product:
        return {"status": "error", "message": "El producto no existe."}

    current_quantity = product['quantity']
    new_quantity = current_quantity + quantity_change

    if new_quantity < 0:
        return {"status": "error", "message": f"No hay suficiente stock."}

    cursor.execute('UPDATE products SET quantity = ? WHERE id = ?', (new_quantity, product_id))
    conn.commit()

    action = "agregado" if quantity_change > 0 else "restado"
    return {
        "status": "success",
        "message": f"Stock actualizado."
    }


def update_product_details(conn, product_id, details_to_update):
    if not details_to_update:
        return {"status": "error", "message": "No se proporcionaron detalles para actualizar."}

    column_mapping = {
        'nuevo_nombre': 'name', 'descripcion': 'description',
        'precio_venta': 'sale_price', 'precio_proveedor': 'supplier_price',
        'ubicacion': 'location'
    }

    fields = [f"{column_mapping[k]} = ?" for k, v in details_to_update.items() if k in column_mapping and v is not None]
    values = [v for k, v in details_to_update.items() if k in column_mapping and v is not None]

    if not fields:
        return {"status": "error", "message": "Campos no válidos para actualizar."}

    values.append(product_id)
    sql_query = f"UPDATE products SET {', '.join(fields)} WHERE id = ?"

    cursor = conn.cursor()
    cursor.execute(sql_query, tuple(values))
    conn.commit()

    return {"status": "success", "message": f"Detalles del producto actualizados."}


def search_products(conn, query):
    cursor = conn.cursor()
    search_query = f"%{query}%"
    cursor.execute('SELECT * FROM products WHERE name LIKE ? OR description LIKE ?', (search_query, search_query))
    return [dict(row) for row in cursor.fetchall()]


def get_all_products(conn):
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products ORDER BY id ASC')
    return [dict(row) for row in cursor.fetchall()]
