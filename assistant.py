import json
import os
import re
from datetime import datetime
import google.generativeai as genai
from inventory import InventoryManager
from billing import BillingManager


class VoiceAssistant:
    """Asistente de voz para gestión de inventario"""

    def __init__(self):
        # Configurar Gemini
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY no encontrada en variables de entorno")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

        # Almacén
        self.warehouse_name = os.getenv('WAREHOUSE_NAME', 'TorniCars')

        # Estado de conversación
        self.conversation_context = []
        self.pending_data = {}

    def get_system_prompt(self):
        """Obtiene el prompt del sistema para el LLM"""
        return f"""
Eres un asistente de voz para el almacén "{self.warehouse_name}". Tu trabajo es ayudar con la gestión de inventario y facturación.

INSTRUCCIONES IMPORTANTES:
1. Siempre responde en español latino de manera natural y amigable
2. Extrae la información del mensaje del usuario y devuelve un JSON con el comando y los datos
3. Si falta información importante, pregunta al usuario antes de ejecutar el comando
4. Los comandos disponibles son:
   - "agregar_producto": Agregar nuevo producto al inventario
   - "buscar_producto": Buscar productos por nombre o descripción
   - "actualizar_producto": Actualizar datos de un producto
   - "listar_productos": Listar todos los productos
   - "crear_factura": Crear una nueva factura
   - "buscar_factura": Buscar una factura específica
   - "listar_facturas": Listar todas las facturas
   - "conversacion": Para respuestas conversacionales sin comando específico

FORMATO DE RESPUESTA:
Tu respuesta DEBE ser SIEMPRE un JSON válido con esta estructura:
{{
    "comando": "nombre_del_comando",
    "mensaje": "Respuesta conversacional para el usuario",
    "datos": {{
        // Datos extraídos del mensaje del usuario
    }},
    "datos_faltantes": [
        // Lista de datos que faltan para completar la operación
    ]
}}

EJEMPLOS:

Usuario: "Agrega 50 tornillos al estante A"
Respuesta:
{{
    "comando": "agregar_producto",
    "mensaje": "Perfecto, voy a agregar 50 tornillos al estante A. ¿Cuál es el precio de venta?",
    "datos": {{
        "nombre": "tornillos",
        "cantidad": 50,
        "ubicacion": "estante A"
    }},
    "datos_faltantes": ["precio_venta"]
}}

Usuario: "Quiero facturar 10 tornillos a Juan Pérez"
Respuesta:
{{
    "comando": "crear_factura",
    "mensaje": "Voy a crear una factura para Juan Pérez con 10 tornillos. ¿Tienes su número de contacto?",
    "datos": {{
        "cliente_nombre": "Juan Pérez",
        "items": [
            {{
                "producto_nombre": "tornillos",
                "cantidad": 10
            }}
        ]
    }},
    "datos_faltantes": ["cliente_contacto"]
}}

REGLAS PARA DATOS:
- Para productos: nombre (obligatorio), descripcion, precio_venta, precio_proveedor, cantidad, ubicacion
- Para facturas: cliente_nombre (obligatorio), cliente_contacto, cliente_email, items (obligatorio)
- Los items de factura necesitan: producto_nombre o producto_id, cantidad (obligatorio)
- Si el usuario no especifica datos importantes, márcalos como faltantes
- Sé inteligente interpretando sinónimos y variaciones del español

Responde SOLO con el JSON, sin texto adicional.
"""

    def process_message(self, user_message):
        """
        Procesa un mensaje del usuario y devuelve la respuesta del asistente

        Args:
            user_message (str): Mensaje del usuario

        Returns:
            dict: Respuesta del asistente
        """
        try:
            # Agregar contexto de conversación
            context = f"Contexto de conversación anterior: {json.dumps(self.conversation_context[-3:])}\n\n"
            full_prompt = self.get_system_prompt() + "\n\n" + context + f"Usuario: {user_message}"

            # Generar respuesta con Gemini
            response = self.model.generate_content(full_prompt)
            response_text = response.text.strip()

            # Limpiar y parsear JSON
            response_text = self._clean_json_response(response_text)
            assistant_response = json.loads(response_text)

            # Validar estructura de respuesta
            required_fields = ['comando', 'mensaje', 'datos']
            if not all(field in assistant_response for field in required_fields):
                raise ValueError("Respuesta del LLM incompleta")

            # Agregar al contexto
            self.conversation_context.append({
                'user': user_message,
                'assistant': assistant_response['mensaje'],
                'timestamp': datetime.now().isoformat()
            })

            # Ejecutar comando si es necesario
            if assistant_response['comando'] != 'conversacion':
                execution_result = self._execute_command(assistant_response)
                assistant_response['resultado_ejecucion'] = execution_result

                # Actualizar mensaje si hubo error en la ejecución
                if not execution_result.get('success', False):
                    assistant_response[
                        'mensaje'] += f" Sin embargo, hubo un problema: {execution_result.get('message', 'Error desconocido')}"

            return assistant_response

        except json.JSONDecodeError as e:
            return {
                'comando': 'conversacion',
                'mensaje': 'Lo siento, hubo un error al procesar tu solicitud. ¿Podrías repetirla de otra manera?',
                'datos': {},
                'error': f'Error JSON: {str(e)}'
            }
        except Exception as e:
            return {
                'comando': 'conversacion',
                'mensaje': 'Disculpa, tuve un problema técnico. ¿Puedes intentar de nuevo?',
                'datos': {},
                'error': str(e)
            }

    def _clean_json_response(self, response_text):
        """Limpia la respuesta del LLM para extraer solo el JSON"""
        # Buscar JSON entre marcadores comunes
        json_patterns = [
            r'```json\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
            r'\{.*\}',
        ]

        for pattern in json_patterns:
            match = re.search(pattern, response_text, re.DOTALL)
            if match:
                return match.group(1) if 'json' in pattern else match.group(0)

        return response_text.strip()

    def _execute_command(self, assistant_response):
        """
        Ejecuta el comando especificado por el asistente

        Args:
            assistant_response (dict): Respuesta del asistente con comando y datos

        Returns:
            dict: Resultado de la ejecución
        """
        comando = assistant_response['comando']
        datos = assistant_response['datos']

        try:
            if comando == 'agregar_producto':
                return self._ejecutar_agregar_producto(datos)
            elif comando == 'buscar_producto':
                return self._ejecutar_buscar_producto(datos)
            elif comando == 'actualizar_producto':
                return self._ejecutar_actualizar_producto(datos)
            elif comando == 'listar_productos':
                return InventoryManager.listar_todos_productos()
            elif comando == 'crear_factura':
                return self._ejecutar_crear_factura(datos)
            elif comando == 'buscar_factura':
                return self._ejecutar_buscar_factura(datos)
            elif comando == 'listar_facturas':
                return BillingManager.listar_facturas()
            else:
                return {'success': False, 'message': f'Comando no reconocido: {comando}'}

        except Exception as e:
            return {'success': False, 'message': f'Error ejecutando comando: {str(e)}'}

    def _ejecutar_agregar_producto(self, datos):
        """Ejecuta el comando de agregar producto"""
        # Verificar datos obligatorios
        if not datos.get('nombre'):
            return {'success': False, 'message': 'El nombre del producto es obligatorio'}

        return InventoryManager.agregar_producto(
            nombre=datos.get('nombre', ''),
            descripcion=datos.get('descripcion', ''),
            precio_venta=datos.get('precio_venta', 0),
            precio_proveedor=datos.get('precio_proveedor', 0),
            cantidad=datos.get('cantidad', 0),
            ubicacion=datos.get('ubicacion', '')
        )

    def _ejecutar_buscar_producto(self, datos):
        """Ejecuta el comando de buscar producto"""
        termino = datos.get('termino') or datos.get('nombre') or datos.get('producto_nombre', '')

        if not termino:
            return {'success': False, 'message': 'Debe especificar un término de búsqueda'}

        return InventoryManager.buscar_productos(termino)

    def _ejecutar_actualizar_producto(self, datos):
        """Ejecuta el comando de actualizar producto"""
        producto_id = datos.get('producto_id')

        if not producto_id:
            # Intentar buscar por nombre
            nombre = datos.get('nombre') or datos.get('producto_nombre')
            if nombre:
                busqueda = InventoryManager.buscar_productos(nombre)
                if busqueda['success'] and len(busqueda['data']) == 1:
                    producto_id = busqueda['data'][0]['id']
                else:
                    return {'success': False, 'message': 'No se pudo identificar el producto a actualizar'}
            else:
                return {'success': False, 'message': 'Debe especificar el producto a actualizar'}

        # Preparar datos de actualización
        datos_actualizacion = {}
        campos_actualizables = ['nombre', 'descripcion', 'precio_venta', 'precio_proveedor', 'cantidad', 'ubicacion']

        for campo in campos_actualizables:
            if campo in datos and datos[campo] is not None:
                datos_actualizacion[campo] = datos[campo]

        return InventoryManager.actualizar_producto(producto_id, **datos_actualizacion)

    def _ejecutar_crear_factura(self, datos):
        """Ejecuta el comando de crear factura"""
        # Verificar datos obligatorios
        if not datos.get('cliente_nombre'):
            return {'success': False, 'message': 'El nombre del cliente es obligatorio'}

        if not datos.get('items') or len(datos.get('items', [])) == 0:
            return {'success': False, 'message': 'Debe especificar productos para la factura'}

        # Procesar items
        items_procesados = []

        for item in datos.get('items', []):
            item_procesado = {}

            # Buscar producto por nombre si no tiene ID
            if not item.get('producto_id') and item.get('producto_nombre'):
                busqueda = InventoryManager.buscar_productos(item['producto_nombre'])
                if busqueda['success'] and len(busqueda['data']) > 0:
                    item_procesado['producto_id'] = busqueda['data'][0]['id']
                else:
                    return {'success': False, 'message': f'No se encontró el producto: {item["producto_nombre"]}'}
            elif item.get('producto_id'):
                item_procesado['producto_id'] = item['producto_id']
            else:
                return {'success': False, 'message': 'Cada item debe tener un producto identificable'}

            # Agregar cantidad
            if not item.get('cantidad') or int(item.get('cantidad', 0)) <= 0:
                return {'success': False, 'message': 'Cada item debe tener una cantidad válida'}

            item_procesado['cantidad'] = int(item['cantidad'])

            # Precio unitario (opcional, se usa el del producto si no se especifica)
            if item.get('precio_unitario'):
                item_procesado['precio_unitario'] = float(item['precio_unitario'])

            items_procesados.append(item_procesado)

        return BillingManager.crear_factura(
            cliente_nombre=datos['cliente_nombre'],
            cliente_contacto=datos.get('cliente_contacto', ''),
            cliente_email=datos.get('cliente_email', ''),
            items=items_procesados
        )

    def _ejecutar_buscar_factura(self, datos):
        """Ejecuta el comando de buscar factura"""
        factura_id = datos.get('factura_id') or datos.get('id')
        numero_factura = datos.get('numero_factura')

        if factura_id:
            return BillingManager.obtener_factura(factura_id)
        elif numero_factura:
            # Buscar por número de factura (implementación simplificada)
            facturas = BillingManager.listar_facturas()
            if facturas['success']:
                for factura in facturas['data']:
                    if factura['numero_factura'] == numero_factura:
                        return BillingManager.obtener_factura(factura['id'])
            return {'success': False, 'message': f'No se encontró la factura: {numero_factura}'}
        else:
            return {'success': False, 'message': 'Debe especificar el ID o número de factura'}

    def clear_context(self):
        """Limpia el contexto de conversación"""
        self.conversation_context = []
        self.pending_data = {}

    def get_conversation_summary(self):
        """Obtiene un resumen de la conversación actual"""
        if not self.conversation_context:
            return "No hay conversación activa"

        return {
            'total_messages': len(self.conversation_context),
            'last_interaction': self.conversation_context[-1] if self.conversation_context else None,
            'warehouse_name': self.warehouse_name
        }