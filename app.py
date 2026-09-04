import os
import json
from flask import Flask, render_template, request, jsonify, g
from dotenv import load_dotenv
import db
import inventory
import billing
import assistant

load_dotenv()
app = Flask(__name__)
app.config['STATIC_FOLDER'] = 'static'


@app.before_request
def before_request():
    g.db_conn = db.get_db_connection()


@app.teardown_request
def teardown_request(exception):
    db_conn = g.pop('db_conn', None)
    if db_conn is not None:
        db_conn.close()


@app.route('/')
def index():
    warehouse_name = os.getenv('WAREHOUSE_NAME', 'TorniCars')
    return render_template('index.html', warehouse_name=warehouse_name)


@app.route('/api/products', methods=['GET'])
def get_products_api():
    products = inventory.get_all_products(g.db_conn)
    return jsonify(products)


# NUEVO ENDPOINT PARA ACTUALIZAR PRODUCTOS DESDE LA UI
@app.route('/api/product/update/<int:product_id>', methods=['POST'])
def update_product_api(product_id):
    data = request.json
    # Mapeo de claves del frontend a las esperadas por la función de actualización
    details_to_update = {
        'nuevo_nombre': data.get('name'),
        'descripcion': data.get('description'),
        'precio_venta': data.get('sale_price'),
        'ubicacion': data.get('location')
    }
    # La cantidad se actualiza por separado
    quantity = data.get('quantity')

    try:
        conn = g.db_conn
        # Actualizar detalles
        inventory.update_product_details(conn, product_id, details_to_update)

        # Actualizar cantidad (stock)
        cursor = conn.cursor()
        cursor.execute('UPDATE products SET quantity = ? WHERE id = ?', (quantity, product_id))
        conn.commit()

        return jsonify({"status": "success", "message": "Producto actualizado correctamente."})
    except Exception as e:
        print(f"Error al actualizar producto: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/ask', methods=['POST'])
def ask_assistant_api():
    data = request.json
    user_text = data.get('text')
    conversation_history = data.get('history', [])

    if not user_text:
        return jsonify({"error": "No se proporcionó texto."}), 400

    llm_response = assistant.process_user_prompt(user_text, conversation_history)

    command = llm_response.get('comando')
    command_data = llm_response.get('datos')
    spoken_response = llm_response.get('respuesta_hablada', "No entendí, ¿puedes repetirlo?")
    execution_result = None

    if command and command_data is not None:
        try:
            conn = g.db_conn
            if command == 'agregar_producto':
                items_to_add = command_data.get('items', [command_data])
                added_count, errors = 0, []
                for item in items_to_add:
                    item_data = {
                        'name': item.get('nombre'), 'description': item.get('descripcion'),
                        'sale_price': item.get('precio_venta'), 'supplier_price': item.get('precio_proveedor'),
                        'quantity': item.get('cantidad'), 'location': item.get('ubicacion')
                    }
                    result = inventory.add_product(conn, **item_data)
                    if result['status'] == 'success':
                        added_count += 1
                    else:
                        errors.append(result['message'])

                if added_count > 0:
                    spoken_response = f"He agregado {added_count} nuevo(s) producto(s) al inventario."
                    if errors:
                        spoken_response += f" Hubo errores con otros: {', '.join(list(set(errors)))}"
                else:
                    spoken_response = f"No pude agregar los productos. Errores: {', '.join(list(set(errors)))}"
                execution_result = {"status": "success"}

            elif command == 'eliminar_producto':
                names_to_delete = command_data.get('nombres_productos', [])
                deleted_count, errors = 0, []
                for name in names_to_delete:
                    product = inventory.find_product_by_name(conn, name)
                    if product:
                        result = inventory.delete_product(conn, product['id'])
                        if result['status'] == 'success':
                            deleted_count += 1
                        else:
                            errors.append(f"Error al borrar '{name}'.")
                    else:
                        errors.append(f"No se encontró '{name}'.")

                if deleted_count > 0:
                    spoken_response = f"He eliminado {deleted_count} producto(s) del inventario."
                else:
                    spoken_response = "No se eliminó ningún producto."
                if errors:
                    spoken_response += f" Errores: {', '.join(errors)}"
                execution_result = {"status": "success"}

            elif command == 'actualizar_stock':
                product = inventory.find_product_by_name(conn, command_data.get('nombre_producto'))
                if product:
                    result = inventory.update_stock(conn, product['id'], command_data.get('cantidad'))
                    spoken_response = result['message']
                else:
                    spoken_response = f"No encontré '{command_data.get('nombre_producto')}'."
                execution_result = {"status": result.get('status', 'error')}

            elif command == 'editar_producto':
                product_name = command_data.pop('nombre_producto', None)
                product = inventory.find_product_by_name(conn, product_name)
                if product:
                    result = inventory.update_product_details(conn, product['id'], command_data)
                    spoken_response = result['message']
                else:
                    spoken_response = f"No encontré el producto '{product_name}'."
                execution_result = {"status": result.get('status', 'error')}

            elif command == 'buscar_producto':
                products_found = inventory.search_products(conn, command_data.get('termino_busqueda'))
                spoken_response = f"Encontré {len(products_found)} productos."
                execution_result = {"products": products_found}

            elif command == 'listar_productos':
                all_products = inventory.get_all_products(conn)
                spoken_response = "Aquí tienes todos los productos."
                execution_result = {"products": all_products}

            elif command == 'crear_factura':
                client_name = command_data.get('nombre_cliente')
                items = command_data.get('items', [])

                if not client_name or not items:
                    spoken_response = "Para crear la factura, necesito el nombre del cliente y al menos un producto."
                else:
                    preview_data = billing.generate_invoice_preview(conn, client_name=client_name, items=items,
                                                                    **command_data)
                    if preview_data['status'] == 'success':
                        spoken_response = "He generado una vista previa de la factura. Por favor, revísala y confírmala."
                        execution_result = {"invoice_preview": preview_data['preview']}
                    else:
                        spoken_response = preview_data['message']

        except Exception as e:
            spoken_response = f"Ocurrió un error al ejecutar el comando: {e}"
            print(f"Error ejecutando comando '{command}': {e}")

    return jsonify({
        "spoken_response": spoken_response,
        "llm_response_json": llm_response,
        "execution_result": execution_result
    })


@app.route('/api/invoice/confirm', methods=['POST'])
def confirm_invoice_api():
    invoice_data = request.json
    try:
        conn = g.db_conn
        result = billing.create_invoice_from_preview(conn, invoice_data)
        return jsonify(result)
    except Exception as e:
        print(f"Error al confirmar factura: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


def setup_database():
    print("Configurando la base de datos...")
    db.create_tables()
    db.init_db_with_examples()
    print("Configuración de la base de datos completada.")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True, ssl_context='adhoc')
