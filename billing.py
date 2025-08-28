import os
from inventory import update_stock

TAX_RATE = float(os.getenv('INVOICE_TAX_RATE', 19.0)) / 100.0


def create_invoice(conn, client_name, client_contact, client_email, items):
    """
    Crea una nueva factura.
    Ahora recibe la conexión a la BD como parámetro y la pasa a las funciones que la necesiten.
    """
    cursor = conn.cursor()

    subtotal = 0
    invoice_items_data = []

    for item in items:
        product_id = item['product_id']
        quantity = item['quantity']

        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        product = cursor.fetchone()

        if not product:
            return {"status": "error", "message": f"El producto con ID {product_id} no existe."}

        if product['quantity'] < quantity:
            return {"status": "error",
                    "message": f"Stock insuficiente para '{product['name']}'. Disponible: {product['quantity']}, Solicitado: {quantity}."}

        item_total = product['sale_price'] * quantity
        subtotal += item_total
        invoice_items_data.append({
            "product_id": product_id,
            "quantity": quantity,
            "unit_price": product['sale_price']
        })

    tax = subtotal * TAX_RATE
    total = subtotal + tax

    try:
        cursor.execute('''
            INSERT INTO invoices (client_name, client_contact, client_email, subtotal, tax, total)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (client_name, client_contact, client_email, subtotal, tax, total))

        invoice_id = cursor.lastrowid

        for item_data in invoice_items_data:
            cursor.execute('''
                INSERT INTO invoice_items (invoice_id, product_id, quantity, unit_price)
                VALUES (?, ?, ?, ?)
            ''', (invoice_id, item_data['product_id'], item_data['quantity'], item_data['unit_price']))

            # Pasamos la misma conexión a update_stock para evitar el bloqueo
            update_stock(conn, item_data['product_id'], -item_data['quantity'])

        conn.commit()

        return {
            "status": "success",
            "message": f"Factura #{invoice_id} creada exitosamente para {client_name}.",
            "invoice_id": invoice_id,
            "total": total
        }

    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": f"Error al crear la factura: {e}"}


def get_invoice_details(conn, invoice_id):
    """
    Obtiene los detalles completos de una factura para su impresión.
    Ahora recibe la conexión a la BD como parámetro.
    """
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM invoices WHERE id = ?', (invoice_id,))
    invoice = cursor.fetchone()
    if not invoice:
        return None

    cursor.execute('''
        SELECT p.id, p.name, ii.quantity, ii.unit_price
        FROM invoice_items ii
        JOIN products p ON ii.product_id = p.id
        WHERE ii.invoice_id = ?
    ''', (invoice_id,))
    items = [dict(row) for row in cursor.fetchall()]

    return {
        "invoice": dict(invoice),
        "items": items
    }
