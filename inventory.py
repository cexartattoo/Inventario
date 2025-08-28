from db import ProductoDB


class InventoryManager:
    """Clase para gestionar el inventario"""

    @staticmethod
    def agregar_producto(nombre, descripcion='', precio_venta=0, precio_proveedor=0, cantidad=0, ubicacion=''):
        """
        Agrega un nuevo producto al inventario

        Args:
            nombre (str): Nombre del producto
            descripcion (str): Descripción del producto
            precio_venta (float): Precio de venta
            precio_proveedor (float): Precio del proveedor
            cantidad (int): Cantidad en stock
            ubicacion (str): Ubicación física del producto

        Returns:
            dict: Resultado de la operación
        """
        try:
            if not nombre.strip():
                return {
                    'success': False,
                    'message': 'El nombre del producto es obligatorio',
                    'data': None
                }

            producto_id = ProductoDB.agregar_producto(
                nombre=nombre.strip(),
                descripcion=descripcion.strip(),
                precio_venta=float(precio_venta) if precio_venta else 0,
                precio_proveedor=float(precio_proveedor) if precio_proveedor else 0,
                cantidad=int(cantidad) if cantidad else 0,
                ubicacion=ubicacion.strip()
            )

            return {
                'success': True,
                'message': f'Producto "{nombre}" agregado correctamente',
                'data': {'producto_id': producto_id}
            }

        except ValueError as e:
            return {
                'success': False,
                'message': f'Error en los datos numéricos: {str(e)}',
                'data': None
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error al agregar producto: {str(e)}',
                'data': None
            }

    @staticmethod
    def buscar_productos(termino):
        """
        Busca productos por nombre o descripción

        Args:
            termino (str): Término de búsqueda

        Returns:
            dict: Resultado de la búsqueda
        """
        try:
            if not termino.strip():
                return {
                    'success': False,
                    'message': 'Debe especificar un término de búsqueda',
                    'data': []
                }

            productos = ProductoDB.buscar_productos(termino.strip())

            return {
                'success': True,
                'message': f'Se encontraron {len(productos)} producto(s)',
                'data': productos
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error en la búsqueda: {str(e)}',
                'data': []
            }

    @staticmethod
    def obtener_producto(producto_id):
        """
        Obtiene un producto por su ID

        Args:
            producto_id (int): ID del producto

        Returns:
            dict: Resultado de la operación
        """
        try:
            producto = ProductoDB.obtener_producto_por_id(int(producto_id))

            if not producto:
                return {
                    'success': False,
                    'message': 'Producto no encontrado',
                    'data': None
                }

            return {
                'success': True,
                'message': 'Producto encontrado',
                'data': producto
            }

        except ValueError:
            return {
                'success': False,
                'message': 'ID de producto inválido',
                'data': None
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error al obtener producto: {str(e)}',
                'data': None
            }

    @staticmethod
    def actualizar_producto(producto_id, **kwargs):
        """
        Actualiza un producto existente

        Args:
            producto_id (int): ID del producto
            **kwargs: Campos a actualizar

        Returns:
            dict: Resultado de la operación
        """
        try:
            producto_id = int(producto_id)

            # Verificar que el producto existe
            producto_actual = ProductoDB.obtener_producto_por_id(producto_id)
            if not producto_actual:
                return {
                    'success': False,
                    'message': 'Producto no encontrado',
                    'data': None
                }

            # Procesar los datos a actualizar
            datos_actualizacion = {}

            for campo, valor in kwargs.items():
                if campo in ['nombre', 'descripcion', 'ubicacion']:
                    if valor is not None:
                        datos_actualizacion[campo] = str(valor).strip()
                elif campo in ['precio_venta', 'precio_proveedor']:
                    if valor is not None and valor != '':
                        datos_actualizacion[campo] = float(valor)
                elif campo == 'cantidad':
                    if valor is not None and valor != '':
                        datos_actualizacion[campo] = int(valor)

            if not datos_actualizacion:
                return {
                    'success': False,
                    'message': 'No hay datos para actualizar',
                    'data': None
                }

            exito = ProductoDB.actualizar_producto(producto_id, **datos_actualizacion)

            if exito:
                return {
                    'success': True,
                    'message': 'Producto actualizado correctamente',
                    'data': {'producto_id': producto_id}
                }
            else:
                return {
                    'success': False,
                    'message': 'No se pudo actualizar el producto',
                    'data': None
                }

        except ValueError as e:
            return {
                'success': False,
                'message': f'Error en los datos: {str(e)}',
                'data': None
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error al actualizar producto: {str(e)}',
                'data': None
            }

    @staticmethod
    def listar_todos_productos():
        """
        Lista todos los productos del inventario

        Returns:
            dict: Resultado de la operación
        """
        try:
            productos = ProductoDB.obtener_todos_productos()

            return {
                'success': True,
                'message': f'Se encontraron {len(productos)} producto(s)',
                'data': productos
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error al listar productos: {str(e)}',
                'data': []
            }

    @staticmethod
    def verificar_stock(producto_id, cantidad_requerida):
        """
        Verifica si hay suficiente stock de un producto

        Args:
            producto_id (int): ID del producto
            cantidad_requerida (int): Cantidad requerida

        Returns:
            dict: Resultado de la verificación
        """
        try:
            producto = ProductoDB.obtener_producto_por_id(int(producto_id))

            if not producto:
                return {
                    'success': False,
                    'message': 'Producto no encontrado',
                    'data': {'disponible': False, 'stock_actual': 0}
                }

            cantidad_requerida = int(cantidad_requerida)
            stock_actual = producto['cantidad']
            disponible = stock_actual >= cantidad_requerida

            return {
                'success': True,
                'message': f'Stock {"suficiente" if disponible else "insuficiente"}',
                'data': {
                    'disponible': disponible,
                    'stock_actual': stock_actual,
                    'cantidad_requerida': cantidad_requerida,
                    'producto_nombre': producto['nombre']
                }
            }

        except ValueError:
            return {
                'success': False,
                'message': 'Datos inválidos',
                'data': {'disponible': False, 'stock_actual': 0}
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error al verificar stock: {str(e)}',
                'data': {'disponible': False, 'stock_actual': 0}
            }

    @staticmethod
    def obtener_productos_bajo_stock(limite=10):
        """
        Obtiene productos con stock bajo

        Args:
            limite (int): Cantidad mínima considerada como stock bajo

        Returns:
            dict: Productos con stock bajo
        """
        try:
            productos = ProductoDB.obtener_todos_productos()
            productos_bajo_stock = [p for p in productos if p['cantidad'] <= limite]

            return {
                'success': True,
                'message': f'Se encontraron {len(productos_bajo_stock)} producto(s) con stock bajo',
                'data': productos_bajo_stock
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error al obtener productos con stock bajo: {str(e)}',
                'data': []
            }