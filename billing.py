from datetime import datetime
from db import FacturaDB, ProductoDB
import os


class BillingManager:
    """Clase para gestionar la facturación"""

    @staticmethod
    def validar_datos_factura(cliente_nombre, items):
        """
        Valida los datos necesarios para crear una factura

        Args:
            cliente_nombre (str): Nombre del cliente
            items (list): Lista de items de la factura

        Returns:
            dict: Resultado de la validación
        """
        errores = []

        # Validar nombre del cliente
        if not cliente_nombre or not cliente_nombre.strip():
            errores.append("El nombre del cliente es obligatorio")

        # Validar items
        if not items or len(items) == 0:
            errores.append("Debe incluir al menos un producto en la factura")

        items_validados = []
        for i, item in enumerate(items):
            item_errores = []

            # Validar producto_id
            if 'producto_id' not in item or not item['producto_id']:
                item_errores.append(f"Item {i + 1}: ID de producto requerido")
            else:
                try:
                    producto_id = int(item['producto_id'])
                    producto = ProductoDB.obtener_producto_por_id(producto_id)
                    if not producto:
                        item_errores.append(f"Item {i + 1}: Producto no encontrado")
                    else:
                        # Validar cantidad
                        cantidad = int(item.get('cantidad', 0))
                        if cantidad <= 0:
                            item_errores.append(f"Item {i + 1}: Cantidad debe ser mayor a 0")
                        elif producto['cantidad'] < cantidad:
                            item_errores.append(f"Item {i + 1}: Stock insuficiente. Disponible: {producto['cantidad']}")

                        # Usar precio de venta del producto si no se especifica
                        precio_unitario = float(item.get('precio_unitario', producto['precio_venta']))
                        if precio_unitario <= 0:
                            item_errores.append(f"Item {i + 1}: Precio debe ser mayor a 0")

                        if not item_errores:
                            items_validados.append({
                                'producto_id': producto_id,
                                'cantidad': cantidad,
                                'precio_unitario': precio_unitario,
                                'producto_nombre': producto['nombre']
                            })

                except (ValueError, TypeError):
                    item_errores.append(f"Item {i + 1}: Datos numéricos inválidos")

            errores.extend(item_errores)

        return {
            'valido': len(errores) == 0,
            'errores': errores,
            'items_validados': items_validados
        }

    @staticmethod
    def crear_factura(cliente_nombre, cliente_contacto='', cliente_email='', items=[], datos_faltantes=None):
        """
        Crea una nueva factura

        Args:
            cliente_nombre (str): Nombre del cliente
            cliente_contacto (str): Contacto del cliente
            cliente_email (str): Email del cliente
            items (list): Lista de items de la factura
            datos_faltantes (dict): Datos que faltan por completar

        Returns:
            dict: Resultado de la operación
        """
        try:
            # Validar datos
            validacion = BillingManager.validar_datos_factura(cliente_nombre, items)

            if not validacion['valido']:
                return {
                    'success': False,
                    'message': 'Datos de factura inválidos',
                    'data': {
                        'errores': validacion['errores'],
                        'datos_faltantes': datos_faltantes or []
                    }
                }

            # Crear la factura
            factura = FacturaDB.crear_factura(
                cliente_nombre=cliente_nombre.strip(),
                cliente_contacto=cliente_contacto.strip(),
                cliente_email=cliente_email.strip(),
                items=validacion['items_validados']
            )

            return {
                'success': True,
                'message': f'Factura {factura["numero_factura"]} creada correctamente',
                'data': factura
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error al crear factura: {str(e)}',
                'data': None
            }

    @staticmethod
    def obtener_factura(factura_id):
        """
        Obtiene una factura completa

        Args:
            factura_id (int): ID de la factura

        Returns:
            dict: Resultado de la operación
        """
        try:
            factura_completa = FacturaDB.obtener_factura_completa(int(factura_id))

            if not factura_completa:
                return {
                    'success': False,
                    'message': 'Factura no encontrada',
                    'data': None
                }

            return {
                'success': True,
                'message': 'Factura encontrada',
                'data': factura_completa
            }

        except ValueError:
            return {
                'success': False,
                'message': 'ID de factura inválido',
                'data': None
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error al obtener factura: {str(e)}',
                'data': None
            }

    @staticmethod
    def listar_facturas():
        """
        Lista todas las facturas

        Returns:
            dict: Resultado de la operación
        """
        try:
            facturas = FacturaDB.obtener_todas_facturas()

            return {
                'success': True,
                'message': f'Se encontraron {len(facturas)} factura(s)',
                'data': facturas
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error al listar facturas: {str(e)}',
                'data': []
            }

    @staticmethod
    def generar_factura_html(factura_id):
        """
        Genera el HTML de una factura para impresión

        Args:
            factura_id (int): ID de la factura

        Returns:
            str: HTML de la factura
        """
        try:
            factura_result = BillingManager.obtener_factura(factura_id)

            if not factura_result['success']:
                return f"<html><body><h1>Error: {factura_result['message']}</h1></body></html>"

            factura_data = factura_result['data']
            factura = factura_data['factura']
            items = factura_data['items']

            # Datos de la empresa
            empresa_nombre = os.getenv('COMPANY_NAME', 'TorniCars S.A.S')
            empresa_nit = os.getenv('COMPANY_NIT', '900123456-1')
            empresa_direccion = os.getenv('COMPANY_ADDRESS', 'Calle 123 #45-67, Bucaramanga')
            empresa_telefono = os.getenv('COMPANY_PHONE', '+57 7 1234567')
            empresa_email = os.getenv('COMPANY_EMAIL', 'info@tornicars.com')

            # Fecha de creación
            fecha_factura = datetime.fromisoformat(factura['fecha_creacion'].replace('Z', '+00:00')).strftime(
                '%d/%m/%Y %H:%M')

            # Generar HTML
            html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Factura {factura['numero_factura']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .company-info {{ margin-bottom: 20px; }}
        .invoice-info {{ display: flex; justify-content: space-between; margin-bottom: 30px; }}
        .customer-info {{ margin-bottom: 30px; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .total-section {{ text-align: right; }}
        .total-row {{ font-weight: bold; }}
        .print-button {{ display: block; margin: 20px auto; padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }}
        @media print {{ .print-button {{ display: none; }} }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{empresa_nombre}</h1>
        <p>NIT: {empresa_nit}</p>
        <p>{empresa_direccion}</p>
        <p>Tel: {empresa_telefono} | Email: {empresa_email}</p>
    </div>

    <div class="invoice-info">
        <div>
            <h2>FACTURA DE VENTA</h2>
            <p><strong>Número:</strong> {factura['numero_factura']}</p>
            <p><strong>Fecha:</strong> {fecha_factura}</p>
        </div>
    </div>

    <div class="customer-info">
        <h3>DATOS DEL CLIENTE</h3>
        <p><strong>Nombre:</strong> {factura['cliente_nombre']}</p>"""

            if factura['cliente_contacto']:
                html += f"<p><strong>Contacto:</strong> {factura['cliente_contacto']}</p>"

            if factura['cliente_email']:
                html += f"<p><strong>Email:</strong> {factura['cliente_email']}</p>"

            html += """
    </div>

    <table>
        <thead>
            <tr>
                <th>Producto</th>
                <th>Cantidad</th>
                <th>Precio Unitario</th>
                <th>Subtotal</th>
            </tr>
        </thead>
        <tbody>"""

            for item in items:
                html += f"""
            <tr>
                <td>{item['producto_nombre']}</td>
                <td>{item['cantidad']}</td>
                <td>${item['precio_unitario']:,.2f}</td>
                <td>${item['subtotal']:,.2f}</td>
            </tr>"""

            html += f"""
        </tbody>
    </table>

    <div class="total-section">
        <p>Subtotal: ${factura['subtotal']:,.2f}</p>
        <p>IVA (19%): ${factura['iva']:,.2f}</p>
        <p class="total-row">TOTAL: ${factura['total']:,.2f}</p>
    </div>

    <button class="print-button" onclick="window.print()">Imprimir Factura</button>

    <script>
        // Auto-imprimir al cargar la página
        window.onload = function() {{
            setTimeout(function() {{
                window.print();
            }}, 500);
        }}
    </script>
</body>
</html>"""

            return html

        except Exception as e:
            return f"<html><body><h1>Error al generar factura: {str(e)}</h1></body></html>"

    @staticmethod
    def calcular_totales(items):
        """
        Calcula los totales de una lista de items

        Args:
            items (list): Lista de items con cantidad y precio_unitario

        Returns:
            dict: Totales calculados
        """
        try:
            subtotal = sum(item['cantidad'] * item['precio_unitario'] for item in items)
            iva = subtotal * 0.19
            total = subtotal + iva

            return {
                'subtotal': round(subtotal, 2),
                'iva': round(iva, 2),
                'total': round(total, 2)
            }

        except Exception as e:
            return {
                'subtotal': 0,
                'iva': 0,
                'total': 0,
                'error': str(e)
            }

    @staticmethod
    def identificar_datos_faltantes_factura(datos):
        """
        Identifica qué datos faltan para completar una factura

        Args:
            datos (dict): Datos actuales de la factura

        Returns:
            list: Lista de datos faltantes
        """
        datos_faltantes = []

        # Datos obligatorios
        if not datos.get('cliente_nombre', '').strip():
            datos_faltantes.append('nombre_cliente')

        if not datos.get('items') or len(datos.get('items', [])) == 0:
            datos_faltantes.append('productos')

        # Validar items
        items = datos.get('items', [])
        for i, item in enumerate(items):
            if not item.get('producto_id'):
                datos_faltantes.append(f'producto_item_{i + 1}')

            if not item.get('cantidad') or int(item.get('cantidad', 0)) <= 0:
                datos_faltantes.append(f'cantidad_item_{i + 1}')

            # Verificar si el producto tiene precio
            if item.get('producto_id'):
                producto = ProductoDB.obtener_producto_por_id(item['producto_id'])
                if producto and producto['precio_venta'] <= 0 and not item.get('precio_unitario'):
                    datos_faltantes.append(f'precio_item_{i + 1}')

        return list(set(datos_faltantes))  # Eliminar duplicados