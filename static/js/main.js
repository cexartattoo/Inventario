// Variables globales
let currentProducts = [];
let currentBills = [];
let recognition = null;
let isListening = false;
let synthesis = window.speechSynthesis;

// Inicialización
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupEventListeners();
    setupSpeechRecognition();
});

// Configuración inicial de la aplicación
function initializeApp() {
    // Cargar tab inicial
    showTab('dashboard');

    // Cargar datos iniciales
    loadStats();
    loadProducts();
    loadBills();

    // Configurar primer item de factura
    addBillItem();
}

// Event listeners
function setupEventListeners() {
    // Navegación por tabs
    document.querySelectorAll('[data-tab]').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const tabName = this.getAttribute('data-tab');
            showTab(tabName);
            updateNavigation(this);
        });
    });

    // Búsqueda de productos
    document.getElementById('searchBtn').addEventListener('click', searchProducts);
    document.getElementById('clearSearchBtn').addEventListener('click', clearSearch);
    document.getElementById('searchProduct').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') searchProducts();
    });

    // Productos
    document.getElementById('saveProductBtn').addEventListener('click', saveProduct);
    document.getElementById('updateProductBtn').addEventListener('click', updateProduct);
    document.getElementById('refreshStats').addEventListener('click', loadStats);

    // Facturación
    document.getElementById('addBillItem').addEventListener('click', addBillItem);
    document.getElementById('billForm').addEventListener('submit', createBill);

    // Asistente de voz
    document.getElementById('voiceBtn').addEventListener('mousedown', startListening);
    document.getElementById('voiceBtn').addEventListener('mouseup', stopListening);
    document.getElementById('voiceBtn').addEventListener('mouseleave', stopListening);
    document.getElementById('sendBtn').addEventListener('click', sendMessage);
    document.getElementById('voiceInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') sendMessage();
    });
    document.getElementById('clearChatBtn').addEventListener('click', clearChat);

    // Auto-calcular totales en facturación
    document.addEventListener('input', function(e) {
        if (e.target.classList.contains('item-quantity') || e.target.classList.contains('item-price')) {
            calculateBillTotals();
        }
    });
}

// Navegación por tabs
function showTab(tabName) {
    // Ocultar todos los tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // Mostrar tab seleccionado
    document.getElementById(tabName).classList.add('active');
}

function updateNavigation(activeLink) {
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    activeLink.classList.add('active');
}

// Funciones de carga de datos
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const result = await response.json();

        if (result.success) {
            const stats = result.data;
            document.getElementById('totalProductos').textContent = stats.total_productos;
            document.getElementById('stockBajo').textContent = stats.productos_stock_bajo;
            document.getElementById('totalFacturas').textContent = stats.total_facturas;
            document.getElementById('valorInventario').textContent = `$${stats.valor_inventario.toLocaleString()}`;

            // Cargar productos con stock bajo
            loadLowStockProducts();
            loadRecentBills();
        }
    } catch (error) {
        showNotification('Error cargando estadísticas', 'error');
    }
}

async function loadProducts() {
    try {
        const response = await fetch('/api/productos');
        const result = await response.json();

        if (result.success) {
            currentProducts = result.data;
            displayProducts(currentProducts);
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        showNotification('Error cargando productos', 'error');
    }
}

async function loadBills() {
    try {
        const response = await fetch('/api/facturas');
        const result = await response.json();

        if (result.success) {
            currentBills = result.data;
            displayBills(currentBills);
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        showNotification('Error cargando facturas', 'error');
    }
}

async function loadLowStockProducts() {
    try {
        const response = await fetch('/api/productos/stock-bajo?limite=10');
        const result = await response.json();

        const container = document.getElementById('productosStockBajo');

        if (result.success && result.data.length > 0) {
            container.innerHTML = result.data.map(product => `
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span>${product.nombre}</span>
                    <span class="badge bg-warning">${product.cantidad}</span>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<p class="text-muted">No hay productos con stock bajo</p>';
        }
    } catch (error) {
        document.getElementById('productosStockBajo').innerHTML = '<p class="text-danger">Error cargando datos</p>';
    }
}

async function loadRecentBills() {
    try {
        const response = await fetch('/api/facturas');
        const result = await response.json();

        const container = document.getElementById('facturasRecientes');

        if (result.success && result.data.length > 0) {
            const recentBills = result.data.slice(0, 5);
            container.innerHTML = recentBills.map(bill => `
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <div>
                        <strong>${bill.numero_factura}</strong><br>
                        <small class="text-muted">${bill.cliente_nombre}</small>
                    </div>
                    <span class="badge bg-success">$${bill.total.toLocaleString()}</span>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<p class="text-muted">No hay facturas recientes</p>';
        }
    } catch (error) {
        document.getElementById('facturasRecientes').innerHTML = '<p class="text-danger">Error cargando datos</p>';
    }
}

// Mostrar productos en tabla
function displayProducts(products) {
    const tbody = document.querySelector('#productsTable tbody');

    if (products.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No se encontraron productos</td></tr>';
        return;
    }

    tbody.innerHTML = products.map(product => {
        const stockClass = getStockClass(product.cantidad);
        return `
            <tr>
                <td>${product.id}</td>
                <td><strong>${product.nombre}</strong></td>
                <td>${product.descripcion || '-'}</td>
                <td>$${product.precio_venta.toLocaleString()}</td>
                <td><span class="stock-indicator ${stockClass}">${product.cantidad}</span></td>
                <td>${product.ubicacion || '-'}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="editProduct(${product.id})">
                        <i class="bi bi-pencil"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function getStockClass(quantity) {
    if (quantity > 20) return 'stock-high';
    if (quantity > 5) return 'stock-medium';
    return 'stock-low';
}

// Mostrar facturas en tabla
function displayBills(bills) {
    const tbody = document.querySelector('#billsTable tbody');

    if (bills.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No se encontraron facturas</td></tr>';
        return;
    }

    tbody.innerHTML = bills.map(bill => `
        <tr>
            <td><strong>${bill.numero_factura}</strong></td>
            <td>${bill.cliente_nombre}</td>
            <td>$${bill.total.toLocaleString()}</td>
            <td>${formatDate(bill.fecha_creacion)}</td>
            <td>
                <button class="btn btn-sm btn-outline-info" onclick="printBill(${bill.id})">
                    <i class="bi bi-printer"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

// Funciones de productos
async function searchProducts() {
    const searchTerm = document.getElementById('searchProduct').value.trim();

    if (!searchTerm) {
        displayProducts(currentProducts);
        return;
    }

    try {
        const response = await fetch('/api/productos/buscar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ termino: searchTerm })
        });

        const result = await response.json();

        if (result.success) {
            displayProducts(result.data);
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        showNotification('Error en la búsqueda', 'error');
    }
}

function clearSearch() {
    document.getElementById('searchProduct').value = '';
    displayProducts(currentProducts);
}

async function saveProduct() {
    const formData = {
        nombre: document.getElementById('productName').value,
        descripcion: document.getElementById('productDescription').value,
        precio_venta: parseFloat(document.getElementById('productSalePrice').value) || 0,
        precio_proveedor: parseFloat(document.getElementById('productSupplierPrice').value) || 0,
        cantidad: parseInt(document.getElementById('productQuantity').value) || 0,
        ubicacion: document.getElementById('productLocation').value
    };

    if (!formData.nombre.trim()) {
        showNotification('El nombre del producto es obligatorio', 'error');
        return;
    }

    try {
        showLoading('Guardando producto...');

        const response = await fetch('/api/productos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        hideLoading();

        if (result.success) {
            showNotification(result.message, 'success');
            document.getElementById('addProductForm').reset();
            bootstrap.Modal.getInstance(document.getElementById('addProductModal')).hide();
            loadProducts();
            loadStats();
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        hideLoading();
        showNotification('Error guardando producto', 'error');
    }
}

async function editProduct(productId) {
    const product = currentProducts.find(p => p.id === productId);

    if (!product) return;

    // Llenar formulario de edición
    document.getElementById('editProductId').value = product.id;
    document.getElementById('editProductName').value = product.nombre;
    document.getElementById('editProductDescription').value = product.descripcion || '';
    document.getElementById('editProductSalePrice').value = product.precio_venta;
    document.getElementById('editProductSupplierPrice').value = product.precio_proveedor;
    document.getElementById('editProductQuantity').value = product.cantidad;
    document.getElementById('editProductLocation').value = product.ubicacion || '';

    // Mostrar modal
    new bootstrap.Modal(document.getElementById('editProductModal')).show();
}

async function updateProduct() {
    const productId = document.getElementById('editProductId').value;
    const formData = {
        nombre: document.getElementById('editProductName').value,
        descripcion: document.getElementById('editProductDescription').value,
        precio_venta: parseFloat(document.getElementById('editProductSalePrice').value) || 0,
        precio_proveedor: parseFloat(document.getElementById('editProductSupplierPrice').value) || 0,
        cantidad: parseInt(document.getElementById('editProductQuantity').value) || 0,
        ubicacion: document.getElementById('editProductLocation').value
    };

    try {
        showLoading('Actualizando producto...');

        const response = await fetch(`/api/productos/${productId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        hideLoading();

        if (result.success) {
            showNotification(result.message, 'success');
            bootstrap.Modal.getInstance(document.getElementById('editProductModal')).hide();
            loadProducts();
            loadStats();
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        hideLoading();
        showNotification('Error actualizando producto', 'error');
    }
}

// Funciones de facturación
function addBillItem() {
    const container = document.getElementById('billItems');
    const itemIndex = container.children.length;

    const itemHtml = `
        <div class="bill-item" data-item-index="${itemIndex}">
            <div class="row">
                <div class="col-md-6">
                    <select class="form-select item-product" required>
                        <option value="">Seleccionar producto</option>
                        ${currentProducts.map(p => `<option value="${p.id}" data-price="${p.precio_venta}">${p.nombre} ($${p.precio_venta})</option>`).join('')}
                    </select>
                </div>
                <div class="col-md-3">
                    <input type="number" class="form-control item-quantity" placeholder="Cantidad" min="1" required>
                </div>
                <div class="col-md-2">
                    <input type="number" class="form-control item-price" placeholder="Precio" step="0.01" min="0">
                </div>
                <div class="col-md-1">
                    <button type="button" class="btn btn-outline-danger btn-sm" onclick="removeBillItem(this)">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
        </div>
    `;

    container.insertAdjacentHTML('beforeend', itemHtml);

    // Agregar event listener para auto-completar precio
    const lastItem = container.lastElementChild;
    const productSelect = lastItem.querySelector('.item-product');
    const priceInput = lastItem.querySelector('.item-price');

    productSelect.addEventListener('change', function() {
        const selectedOption = this.selectedOptions[0];
        if (selectedOption && selectedOption.dataset.price) {
            priceInput.value = selectedOption.dataset.price;
            calculateBillTotals();
        }
    });
}

function removeBillItem(button) {
    button.closest('.bill-item').remove();
    calculateBillTotals();
}

function calculateBillTotals() {
    let subtotal = 0;

    document.querySelectorAll('.bill-item').forEach(item => {
        const quantity = parseFloat(item.querySelector('.item-quantity').value) || 0;
        const price = parseFloat(item.querySelector('.item-price').value) || 0;
        subtotal += quantity * price;
    });

    const iva = subtotal * 0.19;
    const total = subtotal + iva;

    document.getElementById('billSubtotal').textContent = subtotal.toFixed(2);
    document.getElementById('billIva').textContent = iva.toFixed(2);
    document.getElementById('billTotal').textContent = total.toFixed(2);
}

async function createBill(e) {
    e.preventDefault();

    const formData = {
        cliente_nombre: document.getElementById('clientName').value,
        cliente_contacto: document.getElementById('clientContact').value,
        cliente_email: document.getElementById('clientEmail').value,
        items: []
    };

    // Recopilar items
    document.querySelectorAll('.bill-item').forEach(item => {
        const productId = item.querySelector('.item-product').value;
        const quantity = parseInt(item.querySelector('.item-quantity').value) || 0;
        const price = parseFloat(item.querySelector('.item-price').value) || 0;

        if (productId && quantity > 0 && price > 0) {
            formData.items.push({
                producto_id: parseInt(productId),
                cantidad: quantity,
                precio_unitario: price
            });
        }
    });

    if (!formData.cliente_nombre.trim()) {
        showNotification('El nombre del cliente es obligatorio', 'error');
        return;
    }

    if (formData.items.length === 0) {
        showNotification('Debe agregar al menos un producto', 'error');
        return;
    }

    try {
        showLoading('Creando factura...');

        const response = await fetch('/api/facturas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        hideLoading();

        if (result.success) {
            showNotification(`Factura ${result.data.numero_factura} creada correctamente`, 'success');
            document.getElementById('billForm').reset();
            document.getElementById('billItems').innerHTML = '';
            addBillItem();
            calculateBillTotals();
            loadBills();
            loadStats();

            // Preguntar si desea imprimir
            if (confirm('¿Desea imprimir la factura?')) {
                printBill(result.data.id);
            }
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        hideLoading();
        showNotification('Error creando factura', 'error');
    }
}

async function printBill(billId) {
    try {
        window.open(`/api/facturas/${billId}/imprimir`, '_blank');
    } catch (error) {
        showNotification('Error imprimiendo factura', 'error');
    }
}

// Funciones del asistente de voz
function setupSpeechRecognition() {
    if ('webkitSpeechRecognition' in window) {
        recognition = new webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'es-ES';

        recognition.onstart = function() {
            isListening = true;
            updateVoiceUI('listening');
        };

        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            document.getElementById('voiceInput').value = transcript;
            updateVoiceUI('processing');
            sendMessage();
        };

        recognition.onerror = function(event) {
            console.error('Error de reconocimiento:', event.error);
            updateVoiceUI('ready');
            showNotification('Error en el reconocimiento de voz', 'error');
        };

        recognition.onend = function() {
            isListening = false;
            updateVoiceUI('ready');
        };
    } else {
        console.warn('Reconocimiento de voz no soportado');
        document.getElementById('voiceBtn').disabled = true;
        document.getElementById('voiceStatus').textContent = 'Reconocimiento de voz no soportado';
    }
}

function startListening() {
    if (recognition && !isListening) {
        recognition.start();
    }
}

function stopListening() {
    if (recognition && isListening) {
        recognition.stop();
    }
}

function updateVoiceUI(state) {
    const voiceBtn = document.getElementById('voiceBtn');
    const voiceStatus = document.getElementById('voiceStatus');

    voiceBtn.classList.remove('listening', 'processing');
    voiceStatus.classList.remove('listening', 'processing', 'ready');

    switch (state) {
        case 'listening':
            voiceBtn.classList.add('listening');
            voiceStatus.classList.add('listening');
            voiceStatus.textContent = 'Escuchando...';
            voiceBtn.innerHTML = '<i class="bi bi-mic-fill"></i>';
            break;
        case 'processing':
            voiceBtn.classList.add('processing');
            voiceStatus.classList.add('processing');
            voiceStatus.textContent = 'Procesando...';
            voiceBtn.innerHTML = '<i class="bi bi-gear-fill"></i>';
            break;
        case 'ready':
            voiceStatus.classList.add('ready');
            voiceStatus.textContent = 'Listo para escuchar';
            voiceBtn.innerHTML = '<i class="bi bi-mic"></i>';
            break;
    }
}

async function sendMessage() {
    const input = document.getElementById('voiceInput');
    const message = input.value.trim();

    if (!message) return;

    // Mostrar mensaje del usuario
    addChatMessage(message, 'user');
    input.value = '';

    try {
        updateVoiceUI('processing');

        const response = await fetch('/api/assistant/message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });

        const result = await response.json();

        if (result.success) {
            const assistantResponse = result.data;

            // Mostrar respuesta del asistente
            addChatMessage(assistantResponse.mensaje, 'assistant');

            // Reproducir audio si está habilitado
            if (document.getElementById('autoPlayAudio').checked) {
                await playTextToSpeech(assistantResponse.mensaje);
            }

            // Si hubo ejecución de comando, recargar datos relevantes
            if (assistantResponse.resultado_ejecucion) {
                if (assistantResponse.comando.includes('producto')) {
                    loadProducts();
                    loadStats();
                } else if (assistantResponse.comando.includes('factura')) {
                    loadBills();
                    loadStats();
                }
            }

        } else {
            addChatMessage('Lo siento, hubo un error procesando tu mensaje.', 'assistant');
        }

    } catch (error) {
        console.error('Error enviando mensaje:', error);
        addChatMessage('Disculpa, tuve un problema técnico. Intenta de nuevo.', 'assistant');
    } finally {
        updateVoiceUI('ready');
    }
}

function addChatMessage(message, sender) {
    const chatContainer = document.getElementById('chatContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}-message`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = `<strong>${sender === 'user' ? 'Tú' : 'Asistente'}:</strong> ${message}`;

    messageDiv.appendChild(contentDiv);
    chatContainer.appendChild(messageDiv);

    // Scroll al último mensaje
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

async function playTextToSpeech(text) {
    try {
        // Usar Web Speech API si está disponible
        if ('speechSynthesis' in window) {
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'es-ES';
            utterance.rate = 0.9;
            utterance.pitch = 1;
            speechSynthesis.speak(utterance);
        } else {
            // Fallback a servidor (gTTS)
            const response = await fetch('/api/assistant/tts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });

            if (response.ok) {
                const audioBlob = await response.blob();
                const audioUrl = URL.createObjectURL(audioBlob);
                const audio = new Audio(audioUrl);
                audio.play();

                audio.onended = () => {
                    URL.revokeObjectURL(audioUrl);
                };
            }
        }
    } catch (error) {
        console.error('Error reproduciendo audio:', error);
    }
}

function clearChat() {
    document.getElementById('chatContainer').innerHTML = `
        <div class="chat-message assistant-message">
            <div class="message-content">
                <strong>Asistente:</strong> ¡Hola! Soy tu asistente de voz. ¿En qué puedo ayudarte?
            </div>
        </div>
    `;

    // Limpiar contexto en el servidor
    fetch('/api/assistant/context', { method: 'DELETE' });
}

// Funciones de utilidad
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('es-ES', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function showNotification(message, type = 'info', duration = 5000) {
    // Crear elemento de notificación
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.style.minWidth = '300px';

    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(notification);

    // Auto-remover después de la duración especificada
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, duration);
}

function showLoading(text = 'Procesando...') {
    document.getElementById('loadingText').textContent = text;
    const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
    loadingModal.show();
}

function hideLoading() {
    const loadingModal = bootstrap.Modal.getInstance(document.getElementById('loadingModal'));
    if (loadingModal) {
        loadingModal.hide();
    }
}

// Funciones auxiliares para eventos
document.addEventListener('keydown', function(e) {
    // Atajos de teclado
    if (e.ctrlKey || e.metaKey) {
        switch (e.key) {
            case '1':
                e.preventDefault();
                showTab('dashboard');
                updateNavigation(document.querySelector('[data-tab="dashboard"]'));
                break;
            case '2':
                e.preventDefault();
                showTab('inventory');
                updateNavigation(document.querySelector('[data-tab="inventory"]'));
                break;
            case '3':
                e.preventDefault();
                showTab('billing');
                updateNavigation(document.querySelector('[data-tab="billing"]'));
                break;
            case '4':
                e.preventDefault();
                showTab('assistant');
                updateNavigation(document.querySelector('[data-tab="assistant"]'));
                break;
        }
    }
});

// Auto-refresh de estadísticas cada 5 minutos
setInterval(() => {
    if (document.getElementById('dashboard').classList.contains('active')) {
        loadStats();
    }
}, 300000);

// Validación de formularios en tiempo real
document.addEventListener('input', function(e) {
    if (e.target.classList.contains('form-control') && e.target.hasAttribute('required')) {
        if (e.target.value.trim()) {
            e.target.classList.remove('is-invalid');
            e.target.classList.add('is-valid');
        } else {
            e.target.classList.remove('is-valid');
            e.target.classList.add('is-invalid');
        }
    }
});

// Confirmar antes de cerrar si hay datos no guardados
window.addEventListener('beforeunload', function(e) {
    const hasUnsavedData = document.getElementById('billForm').querySelector('input[value], select[value], textarea[value]') ||
                          document.getElementById('addProductForm').querySelector('input[value], select[value], textarea[value]') ||
                          document.getElementById('editProductForm').querySelector('input[value], select[value], textarea[value]');

    if (hasUnsavedData) {
        e.preventDefault();
        e.returnValue = '';
    }
});

console.log(`
╔══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                   ASISTENTE DE VOZ PARA INVENTARIO                                         ║
║                                              Sistema Inicializado                                           ║
╠══════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
║ ✓ Interfaz de usuario cargada                                                                              ║
║ ✓ Reconocimiento de voz configurado                                                                        ║
║ ✓ Síntesis de voz habilitada                                                                              ║
║ ✓ Gestión de inventario lista                                                                             ║
║ ✓ Sistema de facturación operativo                                                                        ║
║                                                                                                            ║
║ Atajos de teclado:                                                                                         ║
║ Ctrl+1: Dashboard | Ctrl+2: Inventario | Ctrl+3: Facturación | Ctrl+4: Asistente                        ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
`);