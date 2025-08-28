from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from flask_socketio import SocketIO
import os
from dotenv import load_dotenv
from db import init_db
from inventory import InventoryManager
from billing import BillingManager
from assistant import VoiceAssistant

# Cargar variables de entorno
load_dotenv()

# Inicializar Flask
app = Flask(__name__)
CORS(app)

# Configurar la clave secreta
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui'
socketio = SocketIO(app, cors_allowed_origins="*")

# Inicializar managers
inventory_manager = InventoryManager()
billing_manager = BillingManager()
voice_assistant = VoiceAssistant()

# Inicializar base de datos
init_db()


@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')


# ========== RUTAS DE INVENTARIO ==========

@app.route('/api/products', methods=['GET'])
def get_products():
    """Obtiene todos los productos"""
    try:
        products = inventory_manager.get_all_products()
        return jsonify({
            'success': True,
            'data': products
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/products/search', methods=['POST'])
def search_products():
    """Busca productos"""
    try:
        data = request.get_json()
        search_term = data.get('search_term', '')

        products = inventory_manager.search_products(search_term)
        return jsonify({
            'success': True,
            'data': products
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/products', methods=['POST'])
def add_product():
    """Agrega un nuevo producto"""
    try:
        data = request.get_json()

        result = inventory_manager.add_product(
            name=data.get('name', ''),
            description=data.get('description', ''),
            sale_price=float(data.get('sale_price', 0)),
            supplier_price=float(data.get('supplier_price', 0)),
            quantity=int(data.get('quantity', 0)),
            physical_location=data.get('physical_location', '')
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """Actualiza un producto"""
    try:
        data = request.get_json()

        # Filtrar solo campos válidos
        update_params = {}
        valid_fields = ['name', 'description', 'sale_price', 'supplier_price', 'quantity', 'physical_location']

        for field in valid_fields:
            if field in data:
                update_params[field] = data[field]

        result = inventory_manager.update_product(product_id, **update_params)
        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/products/<int:product_id>/add-stock', methods=['POST'])
def add_stock(product_id):
    """Agrega stock a un producto"""
    try:
        data = request.get_json()
        quantity = int(data.get('quantity', 0))

        result = inventory_manager.add_stock_to_existing(product_id, quantity)
        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ========== RUTAS DE FACTURACIÓN ==========

@app.route('/api/invoices', methods=['GET'])
def get_invoices():
    """Obtiene todas las facturas"""
    try:
        invoices = billing_manager.get_all_invoices()
        return jsonify({
            'success': True,
            'data': invoices
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/invoices', methods=['POST'])
def create_invoice():
    """Crea una nueva factura"""
    try:
        data = request.get_json()

        result = billing_manager.create_invoice(
            customer_name=data.get('customer_name', ''),
            customer_phone=data.get('customer_phone', ''),
            customer_email=data.get('customer_email', ''),
            items=data.get('items', [])
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/invoices/<int:invoice_id>', methods=['GET'])
def get_invoice(invoice_id):
    """Obtiene una factura específica"""
    try:
        invoice = billing_manager.get_invoice(invoice_id)

        if invoice:
            return jsonify({
                'success': True,
                'data': invoice
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Factura no encontrada'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/invoices/<int:invoice_id>/print', methods=['POST'])
def print_invoice(invoice_id):
    """Imprime una factura"""
    try:
        result = billing_manager.print_invoice(invoice_id)
        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/invoices/<int:invoice_id>/download', methods=['GET'])
def download_invoice(invoice_id):
    """Descarga una factura como archivo de texto"""
    try:
        result = billing_manager.print_invoice(invoice_id)

        if result['success']:
            return send_file(result['filename'], as_attachment=True)
        else:
            return jsonify(result), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ========== RUTAS DEL ASISTENTE DE VOZ ==========

@app.route('/api/voice/process', methods=['POST'])
def process_voice_message():
    """Procesa un mensaje del asistente de voz"""
    try:
        data = request.get_json()
        message = data.get('message', '')

        if not message:
            return jsonify({
                'success': False,
                'message': 'Mensaje vacío'
            }), 400

        result = voice_assistant.process_message(message)
        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'audio_response': 'Lo siento, hubo un error procesando tu solicitud'
        }), 500


@app.route('/api/voice/speak', methods=['POST'])
def text_to_speech():
    """Convierte texto a voz"""
    try:
        data = request.get_json()
        text = data.get('text', '')

        if not text:
            return jsonify({
                'success': False,
                'message': 'Texto vacío'
            }), 400

        success = voice_assistant.text_to_speech(text)

        return jsonify({
            'success': success,
            'message': 'Audio reproducido' if success else 'Error reproduciendo audio'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ========== RUTAS DE CONFIGURACIÓN ==========

@app.route('/api/config', methods=['GET'])
def get_config():
    """Obtiene la configuración actual"""
    try:
        config = {
            'warehouse_name': os.getenv('WAREHOUSE_NAME', 'TorniCars'),
            'company_nit': os.getenv('COMPANY_NIT', '900123456-7'),
            'company_address': os.getenv('COMPANY_ADDRESS', 'Dirección no configurada'),
            'company_phone': os.getenv('COMPANY_PHONE', 'Teléfono no configurado'),
            'company_email': os.getenv('COMPANY_EMAIL', 'Email no configurado')
        }

        return jsonify({
            'success': True,
            'data': config
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ========== MANEJO DE ERRORES ==========

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'message': 'Endpoint no encontrado'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'message': 'Error interno del servidor'
    }), 500


if __name__ == '__main__':
    # Crear carpetas si no existen
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)

    print(f"Iniciando servidor del asistente de voz para {os.getenv('WAREHOUSE_NAME', 'TorniCars')}")
    print("Accede a http://localhost:5000 para usar la aplicación")

    socketio.run(app, host="0.0.0.0", port=5000,allow_unsafe_werkzeug=True)