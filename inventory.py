import sqlite3
from db import get_connection, get_next_reference_number
import difflib


class InventoryManager:

    def __init__(self):
        pass

    def find_similar_products(self, search_term, threshold=0.6):
        """Encuentra productos similares por nombre usando algoritmo de similitud"""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT id, name, description FROM products')
        products = cursor.fetchall()
        conn.close()

        similar_products = []
        search_term_lower = search_term.lower()

        for product_id, name, description in products:
            # Comparar con nombre
            name_similarity = difflib.SequenceMatcher(None, search_term_lower, name.lower()).ratio()

            # Comparar con descripción si existe
            desc_similarity = 0
            if description:
                desc_similarity = difflib.SequenceMatcher(None, search_term_lower, description.lower()).ratio()

            max_similarity = max(name_similarity, desc_similarity)

            if max_similarity >= threshold:
                similar_products.append({
                    'id': product_id,
                    'name': name,
                    'description': description,
                    'similarity': max_similarity
                })

        # Ordenar por similitud descendente
        similar_products.sort(key=lambda x: x['similarity'], reverse=True)
        return similar_products

    def add_product(self, name, description="", sale_price=0.0, supplier_price=0.0,
                    quantity=0, physical_location=""):
        """Agrega un nuevo producto al inventario"""

        # Verificar si existe un producto similar
        similar_products = self.find_similar_products(name, threshold=0.8)

        if similar_products:
            return {
                'success': False,
                'message': f'Ya existe un producto similar: "{similar_products[0]["name"]}". ¿Deseas agregar stock a ese producto en su lugar?',
                'similar_product': similar_products[0],
                'action_needed': 'confirm_add_stock'
            }

        conn = get_connection()
        cursor = conn.cursor()

        reference_number = get_next_reference_number()

        try:
            cursor.execute('''
                INSERT INTO products (reference_number, name, description, sale_price, 
                                    supplier_price, quantity, physical_location)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (reference_number, name, description, sale_price, supplier_price,
                  quantity, physical_location))

            product_id = cursor.lastrowid
            conn.commit()

            return {
                'success': True,
                'message': f'Producto "{name}" agregado exitosamente con referencia #{reference_number}',
                'product_id': product_id,
                'reference_number': reference_number
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error al agregar producto: {str(e)}'
            }
        finally:
            conn.close()

    def add_stock_to_existing(self, product_id, additional_quantity):
        """Agrega stock a un producto existente"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                UPDATE products 
                SET quantity = quantity + ?
                WHERE id = ?
            ''', (additional_quantity, product_id))

            if cursor.rowcount > 0:
                # Obtener información actualizada del producto
                cursor.execute('SELECT name, quantity FROM products WHERE id = ?', (product_id,))
                name, new_quantity = cursor.fetchone()

                conn.commit()
                return {
                    'success': True,
                    'message': f'Se agregaron {additional_quantity} unidades a "{name}". Stock actual: {new_quantity}'
                }
            else:
                return {
                    'success': False,
                    'message': 'Producto no encontrado'
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error al actualizar stock: {str(e)}'
            }
        finally:
            conn.close()

    def search_products(self, search_term):
        """Busca productos por nombre o descripción"""
        conn = get_connection()
        cursor = conn.cursor()

        search_pattern = f'%{search_term}%'
        cursor.execute('''
            SELECT id, reference_number, name, description, sale_price, 
                   quantity, physical_location
            FROM products 
            WHERE name LIKE ? OR description LIKE ?
            ORDER BY name
        ''', (search_pattern, search_pattern))

        products = cursor.fetchall()
        conn.close()

        result = []
        for product in products:
            result.append({
                'id': product[0],
                'reference_number': product[1],
                'name': product[2],
                'description': product[3],
                'sale_price': product[4],
                'quantity': product[5],
                'physical_location': product[6]
            })

        return result

    def get_all_products(self):
        """Obtiene todos los productos del inventario"""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, reference_number, name, description, sale_price, 
                   supplier_price, quantity, physical_location
            FROM products 
            ORDER BY reference_number
        ''')

        products = cursor.fetchall()
        conn.close()

        result = []
        for product in products:
            result.append({
                'id': product[0],
                'reference_number': product[1],
                'name': product[2],
                'description': product[3],
                'sale_price': product[4],
                'supplier_price': product[5],
                'quantity': product[6],
                'physical_location': product[7]
            })

        return result

    def update_product(self, product_id, **kwargs):
        """Actualiza un producto existente"""
        conn = get_connection()
        cursor = conn.cursor()

        # Construir la consulta dinámicamente
        set_clauses = []
        values = []

        for key, value in kwargs.items():
            if key in ['name', 'description', 'sale_price', 'supplier_price',
                       'quantity', 'physical_location']:
                set_clauses.append(f'{key} = ?')
                values.append(value)

        if not set_clauses:
            return {
                'success': False,
                'message': 'No hay campos válidos para actualizar'
            }

        values.append(product_id)

        try:
            cursor.execute(f'''
                UPDATE products 
                SET {', '.join(set_clauses)}
                WHERE id = ?
            ''', values)

            if cursor.rowcount > 0:
                conn.commit()
                return {
                    'success': True,
                    'message': 'Producto actualizado exitosamente'
                }
            else:
                return {
                    'success': False,
                    'message': 'Producto no encontrado'
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error al actualizar producto: {str(e)}'
            }
        finally:
            conn.close()

    def reduce_stock(self, product_id, quantity_to_reduce):
        """Reduce el stock de un producto (para facturación)"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            # Verificar stock actual
            cursor.execute('SELECT name, quantity FROM products WHERE id = ?', (product_id,))
            result = cursor.fetchone()

            if not result:
                return {
                    'success': False,
                    'message': 'Producto no encontrado'
                }

            name, current_quantity = result

            if current_quantity < quantity_to_reduce:
                return {
                    'success': False,
                    'message': f'Stock insuficiente. Disponible: {current_quantity}, solicitado: {quantity_to_reduce}'
                }

            # Reducir stock
            cursor.execute('''
                UPDATE products 
                SET quantity = quantity - ?
                WHERE id = ?
            ''', (quantity_to_reduce, product_id))

            conn.commit()

            new_quantity = current_quantity - quantity_to_reduce
            return {
                'success': True,
                'message': f'Stock reducido. "{name}" ahora tiene {new_quantity} unidades',
                'new_quantity': new_quantity
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error al reducir stock: {str(e)}'
            }
        finally:
            conn.close()

    def get_product_by_id(self, product_id):
        """Obtiene un producto por su ID"""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, reference_number, name, description, sale_price, 
                   supplier_price, quantity, physical_location
            FROM products 
            WHERE id = ?
        ''', (product_id,))

        product = cursor.fetchone()
        conn.close()

        if product:
            return {
                'id': product[0],
                'reference_number': product[1],
                'name': product[2],
                'description': product[3],
                'sale_price': product[4],
                'supplier_price': product[5],
                'quantity': product[6],
                'physical_location': product[7]
            }
        return None