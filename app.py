from flask import Flask, render_template, request, jsonify, send_from_directory, Response
import os
import json
from dotenv import load_dotenv
from db import init_db, ProductoDB, FacturaDB
from inventory import InventoryManager
from billing import BillingManager
from assistant import VoiceAssistant
from gtts import gTTS
import tempfile

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Inicializar base de datos
init_db()

# Instancia global del asistente
voice_assistant = VoiceAssistant()


@app.route('/')
def index():
    """Página principal"""
    warehouse_name = os.getenv('WAREHOUSE_NAME', 'TorniCars')
    return render_template('index.html', warehouse_name=warehouse_name)


# ===== RUTAS DE INVENTARIO =====

@app.route('/api/productos', methods=['GET'])
def listar_productos():
    """Lista todos los productos"""
    resultado = InventoryManager.listar_todos_productos()
    return jsonify(resultado)


@app.route('/api/productos/buscar', methods=['POST'])
def buscar_productos():
    """Busca productos por término"""
    data = request.get_json()
    termino = data.get('termino', '')

    if not termino:
        return jsonify({'success': False, 'message': 'Término de búsqueda requerido'})

    resultado = InventoryManager.buscar_productos(termino)
    return jsonify(resultado)


@app.route('/api/productos', methods=['POST'])
def agregar_producto():
    """Agrega un nuevo producto"""
    data = request.get_json()

    resultado = InventoryManager.agregar_producto(
        nombre=data.get('nombre', ''),
        descripcion=data.get('descripcion', ''),
        precio_venta=data.get('precio_venta', 0),
        precio_proveedor=data.get('precio_proveedor', 0),
        cantidad=data.get('cantidad', 0),
        ubicacion=data.get('ubicacion', '')
    )

    return jsonify(resultado)


@app.route('/api/productos/<int:producto_id>', methods=['GET'])
def obtener_producto(producto_id):
    """Obtiene un producto específico"""
    resultado = InventoryManager.obtener_producto(producto_id)
    return jsonify(resultado)


@app.route('/api/productos/<int:producto_id>', methods=['PUT'])
def actualizar_producto(producto_id):
    """Actualiza un producto existente"""
    data = request.get_json()

    resultado = InventoryManager.actualizar_producto(producto_id, **data)
    return jsonify(resultado)


@app.route('/api/productos/stock-bajo', methods=['GET'])
def productos_stock_bajo():
    """Obtiene productos con stock bajo"""
    limite = request.args.get('limite', 10, type=int)
    resultado = InventoryManager.obtener_productos_bajo_stock(limite)
    return jsonify(resultado)


# ===== RUTAS DE FACTURACIÓN =====

@app.route('/api/facturas', methods=['GET'])
def listar_facturas():
    """Lista todas las facturas"""
    resultado = BillingManager.listar_facturas()
    return jsonify(resultado)


@app.route('/api/facturas', methods=['POST'])
def crear_factura():
    """Crea una nueva factura"""
    data = request.get_json()

    resultado = BillingManager.crear_factura(
        cliente_nombre=data.get('cliente_nombre', ''),
        cliente_contacto=data.get('cliente_contacto', ''),
        cliente_email=data.get('cliente_email', ''),
        items=data.get('items', [])
    )

    return jsonify(resultado)


@app.route('/api/facturas/<int:factura_id>', methods=['GET'])
def obtener_factura(factura_id):
    """Obtiene una factura específica"""
    resultado = BillingManager.obtener_factura(factura_id)
    return jsonify(resultado)


@app.route('/api/facturas/<int:factura_id>/imprimir', methods=['GET'])
def imprimir_factura(factura_id):
    """Genera HTML de factura para impresión"""
    html = BillingManager.generar_factura_html(factura_id)
    return Response(html, mimetype='text/html')


@app.route('/api/facturas/validar', methods=['POST'])
def validar_factura():
    """Valida los datos de una factura antes de crearla"""
    data = request.get_json()

    resultado = BillingManager.validar_datos_factura(
        cliente_nombre=data.get('cliente_nombre', ''),
        items=data.get('items', [])
    )

    return jsonify({
        'success': resultado['valido'],
        'message': 'Datos válidos' if resultado['valido'] else 'Datos inválidos',
        'data': {
            'errores': resultado['errores'],
            'items_validados': resultado.get('items_validados', [])
        }
    })


# ===== RUTAS DEL ASISTENTE DE VOZ =====

@app.route('/api/assistant/message', methods=['POST'])
def process_assistant_message():
    """Procesa un mensaje del asistente de voz"""
    data = request.get_json()
    message = data.get('message', '')

    if not message:
        return jsonify({
            'success': False,
            'message': 'Mensaje requerido'
        })

    try:
        response = voice_assistant.process_message(message)
        return jsonify({
            'success': True,
            'data': response
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error procesando mensaje: {str(e)}'
        })


@app.route('/api/assistant/tts', methods=['POST'])
def text_to_speech():
    """Convierte texto a audio usando gTTS"""
    data = request.get_json()
    text = data.get('text', '')

    if not text:
        return jsonify({'success': False, 'message': 'Texto requerido'})

    try:
        # Crear archivo temporal para el audio
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            tts = gTTS(text=text, lang='es', slow=False)
            tts.save(tmp_file.name)

            # Leer el contenido del archivo
            with open(tmp_file.name, 'rb') as audio_file:
                audio_data = audio_file.read()

            # Limpiar archivo temporal
            os.unlink(tmp_file.name)

            return Response(
                audio_data,
                mimetype='audio/mpeg',
                headers={'Content-Disposition': 'attachment; filename=speech.mp3'}
            )

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error generando audio: {str(e)}'
        })


@app.route('/api/assistant/context', methods=['GET'])
def get_assistant_context():
    """Obtiene el contexto actual del asistente"""
    summary = voice_assistant.get_conversation_summary()
    return jsonify({
        'success': True,
        'data': summary
    })


@app.route('/api/assistant/context', methods=['DELETE'])
def clear_assistant_context():
    """Limpia el contexto del asistente"""
    voice_assistant.clear_context()
    return jsonify({
        'success': True,
        'message': 'Contexto limpiado'
    })


# ===== RUTAS DE UTILIDAD =====

@app.route('/api/config', methods=['GET'])
def get_config():
    """Obtiene la configuración de la aplicación"""
    return jsonify({
        'warehouse_name': os.getenv('WAREHOUSE_NAME', 'TorniCars'),
        'company_name': os.getenv('COMPANY_NAME', 'TorniCars S.A.S'),
        'company_nit': os.getenv('COMPANY_NIT', '900123456-1'),
        'company_address': os.getenv('COMPANY_ADDRESS', 'Calle 123 #45-67, Bucaramanga'),
        'company_phone': os.getenv('COMPANY_PHONE', '+57 7 1234567'),
        'company_email': os.getenv('COMPANY_EMAIL', 'info@tornicars.com')
    })


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Obtiene estadísticas básicas del sistema"""
    try:
        # Estadísticas de productos
        productos_result = InventoryManager.listar_todos_productos()
        total_productos = len(productos_result['data']) if productos_result['success'] else 0

        # Productos con stock bajo
        stock_bajo_result = InventoryManager.obtener_productos_bajo_stock(10)
        productos_stock_bajo = len(stock_bajo_result['data']) if stock_bajo_result['success'] else 0

        # Estadísticas de facturas
        facturas_result = BillingManager.listar_facturas()
        total_facturas = len(facturas_result['data']) if facturas_result['success'] else 0

        # Valor total del inventario
        valor_inventario = 0
        if productos_result['success']:
            for producto in productos_result['data']:
                valor_inventario += producto['precio_venta'] * producto['cantidad']

        return jsonify({
            'success': True,
            'data': {
                'total_productos': total_productos,
                'productos_stock_bajo': productos_stock_bajo,
                'total_facturas': total_facturas,
                'valor_inventario': round(valor_inventario, 2)
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error obteniendo estadísticas: {str(e)}',
            'data': {}
        })


# ===== MANEJO DE ERRORES =====

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Recurso no encontrado'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Error interno del servidor'}), 500


@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Solicitud inválida'}), 400


# ===== MIDDLEWARE =====

@app.before_request
def before_request():
    """Middleware ejecutado antes de cada solicitud"""
    # Permitir CORS para desarrollo
    if request.method == 'OPTIONS':
        response = jsonify({})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response


@app.after_request
def after_request(response):
    """Middleware ejecutado después de cada solicitud"""
    # Permitir CORS para desarrollo
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


if __name__ == '__main__':
    # Configuración para desarrollo
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.getenv('PORT', 5000))

    print(f"""
╔══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                   ASISTENTE DE VOZ PARA INVENTARIO                                         ║
║                                              {os.getenv('WAREHOUSE_NAME', 'TorniCars')}                                              ║
╠══════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
║ Servidor iniciado en: http://localhost:{port}                                                                   ║
║ Modo debug: {'Activado' if debug_mode else 'Desactivado'}                                                                          ║
║ Base de datos: SQLite (inventory.db)                                                                        ║
║ IA: Gemini API                                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
    """)

    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode,
        threaded=True
    )