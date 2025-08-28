import google.generativeai as genai
import json
import os
from dotenv import load_dotenv
from gtts import gTTS
import pygame
import tempfile
from inventory import InventoryManager
from billing import BillingManager

# Cargar variables de entorno
load_dotenv()


class VoiceAssistant:

    def __init__(self):
        # Configurar Gemini API
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY no está configurada en el archivo .env")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

        # Inicializar managers
        self.inventory_manager = InventoryManager()
        self.billing_manager = BillingManager()

        # Inicializar pygame para reproducir audio
        pygame.mixer.init()

        self.system_prompt = """
Eres un asistente de voz para gestión de inventario y facturación. 
Tu nombre es el asistente de {{warehouse_name}}.

REGLAS IMPORTANTES:
1. Siempre responde en español latino, de forma natural y amigable
2. Extrae información de los mensajes del usuario y responde con JSON válido
3. Si falta información crítica, NO generes comando, solo pregunta por lo que falta
4. Si falta información no crítica, genera el comando con campos vacíos

COMANDOS DISPONIBLES:
- "agregar_producto": Agregar nuevo producto al inventario
- "agregar_stock": Agregar cantidad a producto existente  
- "buscar_producto": Buscar productos por nombre/descripción
- "crear_factura": Crear una nueva factura
- "actualizar_producto": Modificar datos de un producto
- "consultar_inventario": Ver todos los productos

FORMATO DE RESPUESTA JSON:
{{
    "comando": "nombre_comando" o null,
    "parametros": {{
        // parámetros específicos del comando
    }},
    "mensaje": "mensaje conversacional para el usuario",
    "informacion_faltante": ["campo1", "campo2"] // si aplica
}}

EJEMPLOS DE COMANDOS:
- Agregar producto: {{"comando": "agregar_producto", "parametros": {{"nombre": "Tornillo M5", "descripcion": "Tornillo métrico 5mm", "cantidad": 100, "precio_venta": 150, "precio_proveedor": 80, "ubicacion": "Estante A"}}}}
- Crear factura: {{"comando": "crear_factura", "parametros": {{"cliente": "Juan Pérez", "telefono": "3001234567", "email": "juan@email.com", "productos": [{{"nombre": "Tornillo M5", "cantidad": 10}}]}}}}

Si el usuario dice algo como "vender tornillos M5", identifica que quiere crear una factura pero le falta información del cliente.
""".format(warehouse_name=os.getenv('WAREHOUSE_NAME', 'TorniCars'))

    def process_message(self, user_message):
        """Procesa un mensaje del usuario y ejecuta la acción correspondiente"""
        try:
            # Generar respuesta del modelo
            full_prompt = f"{self.system_prompt}\n\nUsuario: {user_message}"
            response = self.model.generate_content(full_prompt)

            # Parsear respuesta JSON
            try:
                ai_response = json.loads(response.text)
            except json.JSONDecodeError:
                # Si no es JSON válido, tratar como mensaje simple
                return {
                    'success': True,
                    'message': response.text,
                    'audio_response': response.text
                }

            # Si no hay comando, solo devolver mensaje
            if not ai_response.get('comando'):
                return {
                    'success': True,
                    'message': ai_response.get('mensaje', 'No entendí tu solicitud'),
                    'audio_response': ai_response.get('mensaje', 'No entendí tu solicitud')
                }

            # Ejecutar comando
            return self._execute_command(ai_response)

        except Exception as e:
            return {
                'success': False,
                'message': f'Error al procesar mensaje: {str(e)}',
                'audio_response': 'Lo siento, hubo un error al procesar tu solicitud'
            }

    def _execute_command(self, ai_response):
        """Ejecuta un comando específico"""
        comando = ai_response['comando']
        parametros = ai_response.get('parametros', {})
        mensaje_ia = ai_response.get('mensaje', '')

        try:
            if comando == 'agregar_producto':
                result = self._agregar_producto(parametros)

            elif comando == 'agregar_stock':
                result = self._agregar_stock(parametros)

            elif comando == 'buscar_producto':
                result = self._buscar_producto(parametros)

            elif comando == 'crear_factura':
                result = self._crear_factura(parametros)

            elif comando == 'actualizar_producto':
                result = self._actualizar_producto(parametros)

            elif comando == 'consultar_inventario':
                result = self._consultar_inventario(parametros)

            else:
                result = {
                    'success': False,
                    'message': f'Comando "{comando}" no reconocido'
                }

            # Combinar mensaje de IA con resultado
            if result['success']:
                audio_response = f"{mensaje_ia}. {result['message']}"
            else:
                audio_response = f"{mensaje_ia}. {result['message']}"

            return {
                'success': result['success'],
                'message': result['message'],
                'audio_response': audio_response,
                'data': result.get('data'),
                'action_needed': result.get('action_needed')
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error ejecutando comando {comando}: {str(e)}',
                'audio_response': 'Hubo un error ejecutando la acción solicitada'
            }

    def _agregar_producto(self, parametros):
        """Ejecuta el comando agregar_producto"""
        nombre = parametros.get('nombre', '').strip()

        if not nombre:
            return {
                'success': False,
                'message': 'El nombre del producto es obligatorio'
            }

        result = self.inventory_manager.add_product(
            name=nombre,
            description=parametros.get('descripcion', ''),
            sale_price=parametros.get('precio_venta', 0),
            supplier_price=parametros.get('precio_proveedor', 0),
            quantity=parametros.get('cantidad', 0),
            physical_location=parametros.get('ubicacion', '')
        )

        return result

    def _agregar_stock(self, parametros):
        """Ejecuta el comando agregar_stock"""
        nombre_producto = parametros.get('producto', '').strip()
        cantidad = parametros.get('cantidad', 0)

        if not nombre_producto:
            return {
                'success': False,
                'message': 'Necesito el nombre del producto'
            }

        if cantidad <= 0:
            return {
                'success': False,
                'message': 'La cantidad debe ser mayor a cero'
            }

        # Buscar producto
        productos = self.inventory_manager.search_products(nombre_producto)

        if not productos:
            return {
                'success': False,
                'message': f'No encontré productos con el nombre "{nombre_producto}"'
            }

        # Si hay múltiples, tomar el primero (más similar)
        producto = productos[0]

        result = self.inventory_manager.add_stock_to_existing(
            producto['id'], cantidad
        )

        return result

    def _buscar_producto(self, parametros):
        """Ejecuta el comando buscar_producto"""
        termino = parametros.get('termino', '').strip()

        if not termino:
            return {
                'success': False,
                'message': 'Necesito un término de búsqueda'
            }

        productos = self.inventory_manager.search_products(termino)

        if not productos:
            return {
                'success': True,
                'message': f'No encontré productos que coincidan con "{termino}"',
                'data': []
            }

        # Formatear respuesta
        mensaje = f"Encontré {len(productos)} producto(s):\n"
        for p in productos[:5]:  # Mostrar máximo 5
            mensaje += f"- {p['name']}: {p['quantity']} unidades, ${p['sale_price']}\n"

        return {
            'success': True,
            'message': mensaje.strip(),
            'data': productos
        }

    def _crear_factura(self, parametros):
        """Ejecuta el comando crear_factura"""
        cliente = parametros.get('cliente', '').strip()
        productos = parametros.get('productos', [])

        if not cliente:
            return {
                'success': False,
                'message': 'Necesito el nombre del cliente'
            }

        if not productos:
            return {
                'success': False,
                'message': 'Necesito al menos un producto para facturar'
            }

        # Procesar productos
        items_factura = []

        for item in productos:
            nombre_producto = item.get('nombre', '').strip()
            cantidad = item.get('cantidad', 0)

            if not nombre_producto or cantidad <= 0:
                continue

            # Buscar producto
            productos_encontrados = self.inventory_manager.search_products(nombre_producto)

            if not productos_encontrados:
                return {
                    'success': False,
                    'message': f'Producto "{nombre_producto}" no encontrado en inventario'
                }

            producto = productos_encontrados[0]
            items_factura.append({
                'product_id': producto['id'],
                'quantity': cantidad
            })

        if not items_factura:
            return {
                'success': False,
                'message': 'No se pudieron procesar los productos solicitados'
            }

        # Crear factura
        result = self.billing_manager.create_invoice(
            customer_name=cliente,
            customer_phone=parametros.get('telefono', ''),
            customer_email=parametros.get('email', ''),
            items=items_factura
        )

        return result

    def _actualizar_producto(self, parametros):
        """Ejecuta el comando actualizar_producto"""
        nombre_producto = parametros.get('producto', '').strip()

        if not nombre_producto:
            return {
                'success': False,
                'message': 'Necesito el nombre del producto a actualizar'
            }

        # Buscar producto
        productos = self.inventory_manager.search_products(nombre_producto)

        if not productos:
            return {
                'success': False,
                'message': f'Producto "{nombre_producto}" no encontrado'
            }

        producto = productos[0]

        # Construir parámetros de actualización
        update_params = {}
        if 'precio_venta' in parametros:
            update_params['sale_price'] = parametros['precio_venta']
        if 'precio_proveedor' in parametros:
            update_params['supplier_price'] = parametros['precio_proveedor']
        if 'cantidad' in parametros:
            update_params['quantity'] = parametros['cantidad']
        if 'descripcion' in parametros:
            update_params['description'] = parametros['descripcion']
        if 'ubicacion' in parametros:
            update_params['physical_location'] = parametros['ubicacion']

        if not update_params:
            return {
                'success': False,
                'message': 'No se especificaron campos para actualizar'
            }

        result = self.inventory_manager.update_product(producto['id'], **update_params)
        return result

    def _consultar_inventario(self, parametros):
        """Ejecuta el comando consultar_inventario"""
        productos = self.inventory_manager.get_all_products()

        if not productos:
            return {
                'success': True,
                'message': 'El inventario está vacío',
                'data': []
            }

        mensaje = f"Tienes {len(productos)} productos en inventario:\n"
        for p in productos[:10]:  # Mostrar máximo 10
            mensaje += f"- Ref #{p['reference_number']}: {p['name']} ({p['quantity']} unidades)\n"

        if len(productos) > 10:
            mensaje += f"... y {len(productos) - 10} productos más"

        return {
            'success': True,
            'message': mensaje.strip(),
            'data': productos
        }

    def text_to_speech(self, text):
        """Convierte texto a voz y lo reproduce"""
        try:
            # Crear archivo temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                tts = gTTS(text=text, lang='es', slow=False)
                tts.save(tmp_file.name)

                # Reproducir audio
                pygame.mixer.music.load(tmp_file.name)
                pygame.mixer.music.play()

                # Esperar a que termine
                while pygame.mixer.music.get_busy():
                    pygame.time.wait(100)

                # Limpiar archivo temporal
                os.unlink(tmp_file.name)

                return True

        except Exception as e:
            print(f"Error en text-to-speech: {str(e)}")
            return False