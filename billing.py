import sqlite3
from datetime import datetime
import os
from db import get_connection, get_next_invoice_number
from inventory import InventoryManager


class BillingManager:

    def __init__(self):
        self.inventory_manager = InventoryManager()
        self.tax_rate = 0.19  # IVA del 19%

    def create_invoice(self, customer_name, customer_phone="", customer_email="", items=None):
        """
        Crea una nueva factura
        items: lista de diccionarios con {'product_id': int, 'quantity': int}
        """
        if not items:
            return {
                'success': False,
                'message': 'No se especificaron productos para la factura'
            }

        conn = get_connection()
        cursor = conn.cursor()

        try:
            # Validar productos y calcular totales
            invoice_items = []
            subtotal = 0

            for item in items:
                product_id = item['product_id']
                quantity = item['quantity']

                product = self.inventory_manager.get_product_by_id(product_id)
                if not product:
                    return {
                        'success': False,
                        'message': f'Producto con ID {product_id} no encontrado'
                    }

                if product['sale_price'] is None or product['sale_price'] <= 0:
                    return {
                        'success': False,
                        'message': f'El producto "{product["name"]}" no tiene precio de venta configurado',
                        'action_needed': 'set_price',
                        'product': product
                    }

                if product['quantity'] < quantity:
                    return {
                        'success': False,
                        'message': f'Stock insuficiente para "{product["name"]}". Disponible: {product["quantity"]}, solicitado: {quantity}'
                    }

                item_total = product['sale_price'] * quantity
                subtotal += item_total

                invoice_items.append({
                    'product_id': product_id,
                    'product_name': product['name'],
                    'quantity': quantity,
                    'unit_price': product['sale_price'],
                    'total_price': item_total
                })

            # Calcular impuestos y total
            tax_amount = subtotal * self.tax_rate
            total_amount = subtotal + tax_amount

            # Crear la factura
            invoice_number = get_next_invoice_number()

            cursor.execute('''
                INSERT INTO invoices (invoice_number, customer_name, customer_phone, 
                                    customer_email, subtotal, tax_amount, total_amount)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (invoice_number, customer_name, customer_phone, customer_email,
                  subtotal, tax_amount, total_amount))

            invoice_id = cursor.lastrowid

            # Agregar items de la factura
            for item in invoice_items:
                cursor.execute('''
                    INSERT INTO invoice_items (invoice_id, product_id, product_name,
                                             quantity, unit_price, total_price)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (invoice_id, item['product_id'], item['product_name'],
                      item['quantity'], item['unit_price'], item['total_price']))

                # Reducir stock
                stock_result = self.inventory_manager.reduce_stock(
                    item['product_id'], item['quantity']
                )

                if not stock_result['success']:
                    raise Exception(f"Error al reducir stock: {stock_result['message']}")

            conn.commit()

            return {
                'success': True,
                'message': f'Factura {invoice_number} creada exitosamente',
                'invoice_id': invoice_id,
                'invoice_number': invoice_number,
                'subtotal': subtotal,
                'tax_amount': tax_amount,
                'total_amount': total_amount,
                'items': invoice_items
            }

        except Exception as e:
            conn.rollback()
            return {
                'success': False,
                'message': f'Error al crear factura: {str(e)}'
            }
        finally:
            conn.close()

    def get_invoice(self, invoice_id):
        """Obtiene una factura completa con sus items"""
        conn = get_connection()
        cursor = conn.cursor()

        # Obtener datos de la factura
        cursor.execute('''
            SELECT invoice_number, customer_name, customer_phone, customer_email,
                   subtotal, tax_amount, total_amount, created_at
            FROM invoices
            WHERE id = ?
        ''', (invoice_id,))

        invoice_data = cursor.fetchone()

        if not invoice_data:
            conn.close()
            return None

        # Obtener items de la factura
        cursor.execute('''
            SELECT product_name, quantity, unit_price, total_price
            FROM invoice_items
            WHERE invoice_id = ?
        ''', (invoice_id,))

        items = cursor.fetchall()
        conn.close()

        return {
            'invoice_number': invoice_data[0],
            'customer_name': invoice_data[1],
            'customer_phone': invoice_data[2],
            'customer_email': invoice_data[3],
            'subtotal': invoice_data[4],
            'tax_amount': invoice_data[5],
            'total_amount': invoice_data[6],
            'created_at': invoice_data[7],
            'items': [{
                'product_name': item[0],
                'quantity': item[1],
                'unit_price': item[2],
                'total_price': item[3]
            } for item in items]
        }

    def get_all_invoices(self):
        """Obtiene todas las facturas"""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, invoice_number, customer_name, total_amount, created_at
            FROM invoices
            ORDER BY created_at DESC
        ''')

        invoices = cursor.fetchall()
        conn.close()

        return [{
            'id': invoice[0],
            'invoice_number': invoice[1],
            'customer_name': invoice[2],
            'total_amount': invoice[3],
            'created_at': invoice[4]
        } for invoice in invoices]

    def generate_invoice_text(self, invoice_id):
        """Genera el texto de la factura para impresión"""
        invoice = self.get_invoice(invoice_id)

        if not invoice:
            return "Factura no encontrada"

        # Obtener información de la empresa desde variables de entorno
        warehouse_name = os.getenv('WAREHOUSE_NAME', 'TorniCars')
        company_nit = os.getenv('COMPANY_NIT', '900123456-7')
        company_address = os.getenv('COMPANY_ADDRESS', 'Dirección no configurada')
        company_phone = os.getenv('COMPANY_PHONE', 'Teléfono no configurado')
        company_email = os.getenv('COMPANY_EMAIL', 'Email no configurado')

        # Formatear fecha
        created_at = datetime.fromisoformat(invoice['created_at'])
        formatted_date = created_at.strftime('%d/%m/%Y %H:%M')

        # Construir texto de la factura
        text = f"""
=====================================
           {warehouse_name}
=====================================
NIT: {company_nit}
{company_address}
Tel: {company_phone}
Email: {company_email}

-------------------------------------
FACTURA: {invoice['invoice_number']}
FECHA: {formatted_date}
-------------------------------------

CLIENTE: {invoice['customer_name']}
TELÉFONO: {invoice['customer_phone']}
EMAIL: {invoice['customer_email']}

-------------------------------------
PRODUCTOS
-------------------------------------
"""

        # Agregar productos
        for item in invoice['items']:
            text += f"""
{item['product_name']}
Cant: {item['quantity']} x ${item['unit_price']:,.2f}
                    ${item['total_price']:,.2f}
"""

        # Agregar totales
        text += f"""
-------------------------------------
SUBTOTAL:           ${invoice['subtotal']:,.2f}
IVA (19%):          ${invoice['tax_amount']:,.2f}
TOTAL:              ${invoice['total_amount']:,.2f}
=====================================

Gracias por su compra!
"""

        return text

    def print_invoice(self, invoice_id):
        """Envía la factura a la impresora (simulado)"""
        invoice_text = self.generate_invoice_text(invoice_id)

        # En un entorno real, aquí enviarías a la impresora
        # Por ahora, guardamos en un archivo
        filename = f"factura_{invoice_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(invoice_text)

            return {
                'success': True,
                'message': f'Factura guardada en {filename}',
                'filename': filename
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error al guardar factura: {str(e)}'
            }