import os
from datetime import datetime
from inventory import update_stock, find_product_by_name

TAX_RATE = float(os.getenv('INVOICE_TAX_RATE', 19.0)) / 100.0


def generate_invoice_preview(conn, client_name, items, **kwargs):
    """
    Genera una vista previa de la factura sin guardarla en la BD.
    Verifica el stock y calcula los totales.
    """
    subtotal = 0
    preview_items = []

    for item_data in items:
        product = find_product_by_name(conn, item_data['nombre_producto'])
        quantity = item_data['quantity']

        if not product:
            return {"status": "error", "message": f"El producto '{item_data['nombre_producto']}' no existe."}

        if product['quantity'] < quantity:
            return {"status": "error",
                    "message": f"Stock insuficiente para '{product['name']}'. Disponible: {product['quantity']}, Solicitado: {quantity}."}

        item_total = product['sale_price'] * quantity
        subtotal += item_total
        preview_items.append({
            "product_id": product['id'],
            "name": product['name'],
            "quantity": quantity,
            "unit_price": product['sale_price']
        })

    tax = subtotal * TAX_RATE
    total = subtotal + tax

    preview = {
        "client_name": client_name,
        "client_contact": kwargs.get('contacto_cliente'),
        "client_email": kwargs.get('email_cliente'),
        "created_at": datetime.now().isoformat(),
        "items": preview_items,
        "subtotal": subtotal,
        "tax": tax,
        "total": total
    }

    return {"status": "success", "preview": preview}


def create_invoice_from_preview(conn, invoice_data):
    """
    Crea la factura final en la BD a partir de los datos de la vista previa
    y descuenta el stock.
    """
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO invoices (client_name, client_contact, client_email, subtotal, tax, total)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            invoice_data['client_name'],
            invoice_data.get('client_contact'),
            invoice_data.get('client_email'),
            invoice_data['subtotal'],
            invoice_data['tax'],
            invoice_data['total']
        ))

        invoice_id = cursor.lastrowid

        for item_data in invoice_data['items']:
            cursor.execute('''
                INSERT INTO invoice_items (invoice_id, product_id, quantity, unit_price)
                VALUES (?, ?, ?, ?)
            ''', (invoice_id, item_data['product_id'], item_data['quantity'], item_data['unit_price']))

            update_stock(conn, item_data['product_id'], -item_data['quantity'])

        conn.commit()

        return {
            "status": "success",
            "message": f"Factura #{invoice_id} confirmada y guardada exitosamente.",
            "invoice_id": invoice_id
        }

    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": f"Error al crear la factura: {e}"}


def get_invoice_details(conn, invoice_id):
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
