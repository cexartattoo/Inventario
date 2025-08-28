// Variables globales
let isListening = false;
let recognition = null;
let currentProducts = [];
let currentInvoiceId = null;

// Inicialización cuando se carga la página
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Cargar configuración
    loadConfig();

    // Cargar datos iniciales
    loadProducts();
    loadInvoices();

    // Configurar reconocimiento de voz
    initVoiceRecognition();

    // Configurar eventos
    setupEventListeners();

    // Mostrar pestaña de inventario por defecto
    showTab('inventory');
}

function loadConfig() {
    fetch('/api/config')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('warehouse-name').textContent = data.data.warehouse_name;
            }
        })
        .catch(error => console.error('Error cargando configuración:', error));
}

function setupEventListeners() {
    // Formulario de productos
    document.getElementById('product-form').addEventListener('submit', handleAddProduct);

    // Formulario de facturas
    document.getElementById('invoice-form').addEventListener('submit', handleCreateInvoice);

    // Entrada de texto para asistente
    document.getElementById('text-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendTextMessage();
        }
    });

    // Búsqueda de productos
    document.getElementById('search-products').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchProducts();
        }
    });
}

// ============ GESTIÓN DE PESTAÑAS ============
function showTab(tabName) {
    // Ocultar todas las pestañas
    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.remove('active');
    });

    // Mostrar pestaña seleccionada
    document.getElementById(tabName + '-panel').classList.add('active');

    // Actualizar estado de navegación
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });

    event.target.classList.add('active');
}

// ============ GESTIÓN DE PRODUCTOS ============
function loadProducts() {
    fetch('/api/products')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentProducts = data.data;
                displayProducts(data.data);
                updateProductsDatalist(data.data);
            } else {
                showError('Error cargando productos: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showError('Error de conexión al cargar productos');
        });
}

function displayProducts(products) {
    const tbody = document.getElementById('products-table-body');

    if (products.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-muted">
                    <i class="fas fa-inbox me-2"></i>No hay productos en el inventario
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = products.map(product => `
        <tr>
            <td><strong>#${product.reference_number}</strong></td>
            <td>${product.name}</td>
            <td>${product.description || '<em>Sin descripción</em>'}</td>
            <td>$${formatPrice(product.sale_price)}</td>
            <td>
                <span class="badge ${getStockBadgeClass(product.quantity)}">
                    ${product.quantity}
                </span>
            </td>
            <td>${product.physical_location || '<em>Sin ubicar</em>'}</td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="editProduct(${product.id})" title="Editar">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-outline-success" onclick="showAddStockModal(${product.id}, '${product.name}', ${product.quantity})" title="Agregar stock">
                        <i class="fas fa-plus"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

function getStockBadgeClass(quantity) {
    if (quantity === 0) return 'badge-out-of-stock';
    if (quantity <= 5) return 'badge-low-stock';
    return 'badge-in-stock';
}

function formatPrice(price) {
    return new Intl.NumberFormat('es-CO', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(price || 0);
}

function searchProducts() {
    const searchTerm = document.getElementById('search-products').value.trim();

    if (!searchTerm) {
        displayProducts(currentProducts);
        return;
    }

    fetch('/api/products/search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ search_term: searchTerm })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displayProducts(data.data);
        } else {
            showError('Error en búsqueda: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showError('Error de conexión en búsqueda');
    });
}

function handleAddProduct(e) {
    e.preventDefault();

    const formData = {
        name: document.getElementById('product-name').value,
        description: document.getElementById('product-description').value,
        sale_price: parseFloat(document.getElementById('product-sale-price').value) || 0,
        supplier_price: parseFloat(document.getElementById('product-supplier-price').value) || 0,
        quantity: parseInt(document.getElementById('product-quantity').value) || 0,
        physical_location: document.getElementById('product-location').value
    };

    fetch('/api/products', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(data.message);
            document.getElementById('product-form').reset();
            loadProducts();
        } else {
            showError(data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showError('Error de conexión al agregar producto');
    });
}

function editProduct(productId) {
    const product = currentProducts.find(p => p.id === productId);
    if (!product) return;

    // Llenar formulario de edición
    document.getElementById('edit-product-id').value = product.id;
    document.getElementById('edit-product-name').value = product.name;
    document.getElementById('edit-product-description').value = product.description || '';
    document.getElementById('edit-product-sale-price').value = product.sale_price || '';
    document.getElementById('edit-product-supplier-price').value = product.supplier_price || '';
    document.getElementById('edit-product-quantity').value = product.quantity || '';
    document.getElementById('edit-product-location').value = product.physical_location || '';

    // Mostrar modal
    new bootstrap.Modal(document.getElementById('editProductModal')).show();
}

function saveProductChanges() {
    const productId = document.getElementById('edit-product-id').value;
    const formData = {
        name: document.getElementById('edit-product-name').value,
        description: document.getElementById('edit-product-description').value,
        sale_price: parseFloat(document.getElementById('edit-product-sale-price').value) || 0,
        supplier_price: parseFloat(document.getElementById('edit-product-supplier-price').value) || 0,
        quantity: parseInt(document.getElementById('edit-product-quantity').value) || 0,
        physical_location: document.getElementById('edit-product-location').value
    };

    fetch(`/api/products/${productId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(data.message);
            bootstrap.Modal.getInstance(document.getElementById('editProductModal')).hide();
            loadProducts();
        } else {
            showError(data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showError('Error de conexión al actualizar producto');
    });
}

function showAddStockModal(productId, productName, currentQuantity) {
    document.getElementById('stock-product-id').value = productId;
    document.getElementById('stock-product-name').textContent = productName;
    document.getElementById('stock-current-quantity').textContent = currentQuantity;
    document.getElementById('stock-quantity').value = 1;

    new bootstrap.Modal(document.getElementById('addStockModal')).show();
}

function addStock() {
    const productId = document.getElementById('stock-product-id').value;
    const quantity = parseInt(document.getElementById('stock-quantity').value);

    if (quantity <= 0) {
        showError('La cantidad debe ser mayor a cero');
        return;
    }

    fetch(`/api/products/${productId}/add-stock`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ quantity: quantity })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(data.message);
            bootstrap.Modal.getInstance(document.getElementById('addStockModal')).hide();
            loadProducts();
        } else {
            showError(data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showError('Error de conexión al agregar stock');
    });
}

function updateProductsDatalist(products) {
    const datalist = document.getElementById('products-datalist');
    datalist.innerHTML = products.map(product =>
        `<option value="${product.name}" data-id="${product.id}" data-price="${product.sale_price}">`
    ).join('');
}

// ============ GESTIÓN DE FACTURACIÓN ============
function loadInvoices() {
    fetch('/api/invoices')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayInvoices(data.data);
            } else {
                showError('Error cargando facturas: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showError('Error de conexión al cargar facturas');
        });
}

function displayInvoices(invoices) {
    const tbody = document.getElementById('invoices-table-body');

    if (invoices.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center text-muted">
                    <i class="fas fa-file-invoice me-2"></i>No hay facturas registradas
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = invoices.map(invoice => `
        <tr>
            <td><strong>${invoice.invoice_number}</strong></td>
            <td>${invoice.customer_name}</td>
            <td>${formatPrice(invoice.total_amount)}</td>
            <td>${formatDate(invoice.created_at)}</td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="viewInvoice(${invoice.id})" title="Ver detalles">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-outline-secondary" onclick="printInvoice(${invoice.id})" title="Imprimir">
                        <i class="fas fa-print"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('es-CO', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function addInvoiceItem() {
    const container = document.getElementById('invoice-items');
    const newItem = document.createElement('div');
    newItem.className = 'invoice-item mb-3';
    newItem.innerHTML = `
        <div class="row">
            <div class="col-8">
                <input type="text" class="form-control product-search" placeholder="Buscar producto..." list="products-datalist">
            </div>
            <div class="col-3">
                <input type="number" class="form-control product-quantity" placeholder="Cantidad" min="1">
            </div>
            <div class="col-1">
                <button type="button" class="btn-remove" onclick="removeInvoiceItem(this)">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        </div>
    `;
    container.appendChild(newItem);

    // Agregar eventos para cálculo automático
    setupInvoiceItemEvents(newItem);
}

function removeInvoiceItem(button) {
    button.closest('.invoice-item').remove();
    calculateInvoiceTotal();
}

function setupInvoiceItemEvents(item) {
    const productSearch = item.querySelector('.product-search');
    const quantity = item.querySelector('.product-quantity');

    [productSearch, quantity].forEach(input => {
        input.addEventListener('input', calculateInvoiceTotal);
    });
}

function calculateInvoiceTotal() {
    let total = 0;

    document.querySelectorAll('.invoice-item').forEach(item => {
        const productName = item.querySelector('.product-search').value;
        const quantity = parseInt(item.querySelector('.product-quantity').value) || 0;

        const product = currentProducts.find(p => p.name === productName);
        if (product && quantity > 0) {
            total += product.sale_price * quantity;
        }
    });

    // Agregar IVA (19%)
    const tax = total * 0.19;
    const finalTotal = total + tax;

    document.getElementById('invoice-total').textContent = `${formatPrice(finalTotal)}`;
}

function handleCreateInvoice(e) {
    e.preventDefault();

    const customerName = document.getElementById('customer-name').value.trim();
    const customerPhone = document.getElementById('customer-phone').value.trim();
    const customerEmail = document.getElementById('customer-email').value.trim();

    if (!customerName) {
        showError('El nombre del cliente es obligatorio');
        return;
    }

    // Recopilar productos
    const items = [];
    document.querySelectorAll('.invoice-item').forEach(item => {
        const productName = item.querySelector('.product-search').value.trim();
        const quantity = parseInt(item.querySelector('.product-quantity').value) || 0;

        if (productName && quantity > 0) {
            const product = currentProducts.find(p => p.name === productName);
            if (product) {
                items.push({
                    product_id: product.id,
                    quantity: quantity
                });
            }
        }
    });

    if (items.length === 0) {
        showError('Debe agregar al menos un producto a la factura');
        return;
    }

    const invoiceData = {
        customer_name: customerName,
        customer_phone: customerPhone,
        customer_email: customerEmail,
        items: items
    };

    fetch('/api/invoices', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(invoiceData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(`Factura ${data.invoice_number} creada exitosamente`);
            document.getElementById('invoice-form').reset();
            document.getElementById('invoice-total').textContent = '$0.00';

            // Mantener solo un item de producto
            const container = document.getElementById('invoice-items');
            container.innerHTML = `
                <div class="invoice-item mb-3">
                    <div class="row">
                        <div class="col-8">
                            <input type="text" class="form-control product-search" placeholder="Buscar producto..." list="products-datalist">
                        </div>
                        <div class="col-4">
                            <input type="number" class="form-control product-quantity" placeholder="Cantidad" min="1">
                        </div>
                    </div>
                </div>
            `;
            setupInvoiceItemEvents(container.querySelector('.invoice-item'));

            loadInvoices();
            loadProducts(); // Recargar productos para actualizar stock
        } else {
            showError(data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showError('Error de conexión al crear factura');
    });
}

function viewInvoice(invoiceId) {
    fetch(`/api/invoices/${invoiceId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayInvoiceDetails(data.data);
                currentInvoiceId = invoiceId;
                new bootstrap.Modal(document.getElementById('viewInvoiceModal')).show();
            } else {
                showError('Error cargando factura: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showError('Error de conexión al cargar factura');
        });
}

function displayInvoiceDetails(invoice) {
    const container = document.getElementById('invoice-details');

    container.innerHTML = `
        <div class="row mb-3">
            <div class="col-md-6">
                <h6>Información de la Factura</h6>
                <p><strong>Número:</strong> ${invoice.invoice_number}</p>
                <p><strong>Fecha:</strong> ${formatDate(invoice.created_at)}</p>
            </div>
            <div class="col-md-6">
                <h6>Información del Cliente</h6>
                <p><strong>Nombre:</strong> ${invoice.customer_name}</p>
                <p><strong>Teléfono:</strong> ${invoice.customer_phone || 'No especificado'}</p>
                <p><strong>Email:</strong> ${invoice.customer_email || 'No especificado'}</p>
            </div>
        </div>

        <h6>Productos</h6>
        <div class="table-responsive">
            <table class="table table-sm">
                <thead>
                    <tr>
                        <th>Producto</th>
                        <th>Cantidad</th>
                        <th>Precio Unit.</th>
                        <th>Total</th>
                    </tr>
                </thead>
                <tbody>
                    ${invoice.items.map(item => `
                        <tr>
                            <td>${item.product_name}</td>
                            <td>${item.quantity}</td>
                            <td>${formatPrice(item.unit_price)}</td>
                            <td>${formatPrice(item.total_price)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>

        <div class="row mt-3">
            <div class="col-md-6"></div>
            <div class="col-md-6">
                <table class="table table-sm">
                    <tr>
                        <td><strong>Subtotal:</strong></td>
                        <td class="text-end">${formatPrice(invoice.subtotal)}</td>
                    </tr>
                    <tr>
                        <td><strong>IVA (19%):</strong></td>
                        <td class="text-end">${formatPrice(invoice.tax_amount)}</td>
                    </tr>
                    <tr class="table-primary">
                        <td><strong>TOTAL:</strong></td>
                        <td class="text-end"><strong>${formatPrice(invoice.total_amount)}</strong></td>
                    </tr>
                </table>
            </div>
        </div>
    `;

    // Configurar botón de impresión
    document.getElementById('print-invoice-btn').onclick = () => printInvoice(currentInvoiceId);
}

function printInvoice(invoiceId) {
    fetch(`/api/invoices/${invoiceId}/print`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(data.message);
        } else {
            showError('Error al imprimir: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showError('Error de conexión al imprimir');
    });
}

// ============ ASISTENTE DE VOZ ============
function initVoiceRecognition() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();

        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'es-ES';

        recognition.onstart = function() {
            isListening = true;
            updateVoiceButton();
        };

        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            processVoiceMessage(transcript);
        };

        recognition.onerror = function(event) {
            console.error('Error de reconocimiento de voz:', event.error);
            showError('Error en el reconocimiento de voz: ' + event.error);
            isListening = false;
            updateVoiceButton();
        };

        recognition.onend = function() {
            isListening = false;
            updateVoiceButton();
        };
    } else {
        console.warn('El reconocimiento de voz no está soportado en este navegador');
        document.getElementById('voice-status').textContent = 'Reconocimiento de voz no disponible';
    }
}

function toggleVoiceRecognition() {
    if (!recognition) {
        showError('Reconocimiento de voz no disponible');
        return;
    }

    if (isListening) {
        recognition.stop();
    } else {
        recognition.start();
    }
}

function updateVoiceButton() {
    const btn = document.getElementById('voice-btn');
    const status = document.getElementById('voice-status');

    if (isListening) {
        btn.classList.add('listening');
        status.textContent = 'Escuchando...';
    } else {
        btn.classList.remove('listening', 'processing');
        status.textContent = 'Mantener para hablar';
    }
}

function processVoiceMessage(message) {
    if (!message.trim()) return;

    // Mostrar mensaje del usuario en el chat
    addChatMessage(message, 'user');

    // Mostrar estado de procesamiento
    const btn = document.getElementById('voice-btn');
    const status = document.getElementById('voice-status');
    btn.classList.add('processing');
    status.textContent = 'Procesando...';

    // Enviar mensaje al asistente
    fetch('/api/voice/process', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: message })
    })
    .then(response => response.json())
    .then(data => {
        // Mostrar respuesta del asistente
        addChatMessage(data.message || data.audio_response, 'assistant');

        // Reproducir respuesta de voz si está disponible
        if (data.audio_response && 'speechSynthesis' in window) {
            speakText(data.audio_response);
        }

        // Si hubo cambios en los datos, recargar
        if (data.success) {
            setTimeout(() => {
                loadProducts();
                loadInvoices();
            }, 1000);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        addChatMessage('Lo siento, hubo un error procesando tu solicitud.', 'assistant');
    })
    .finally(() => {
        btn.classList.remove('processing');
        status.textContent = 'Mantener para hablar';
    });
}

function sendTextMessage() {
    const input = document.getElementById('text-input');
    const message = input.value.trim();

    if (!message) return;

    input.value = '';
    processVoiceMessage(message);
}

function addChatMessage(message, sender) {
    const container = document.getElementById('chat-container');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}-message`;

    const now = new Date().toLocaleTimeString('es-CO', {
        hour: '2-digit',
        minute: '2-digit'
    });

    messageDiv.innerHTML = `
        <div class="message-content">
            ${sender === 'assistant' ? '<i class="fas fa-robot me-2"></i>' : ''}
            ${message}
        </div>
        <div class="message-time">${now}</div>
    `;

    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
}

function speakText(text) {
    if ('speechSynthesis' in window) {
        // Cancelar cualquier síntesis en curso
        speechSynthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'es-ES';
        utterance.rate = 0.9;
        utterance.pitch = 1;

        speechSynthesis.speak(utterance);
    }
}

// ============ UTILIDADES ============
function showSuccess(message) {
    showAlert(message, 'success');
}

function showError(message) {
    showAlert(message, 'danger');
}

function showAlert(message, type) {
    // Crear elemento de alerta
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 400px;';

    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(alert);

    // Auto-remover después de 5 segundos
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 5000);
}

// Inicializar eventos de elementos dinámicos cuando se carga la página
document.addEventListener('DOMContentLoaded', function() {
    // Configurar el primer item de factura
    const firstInvoiceItem = document.querySelector('.invoice-item');
    if (firstInvoiceItem) {
        setupInvoiceItemEvents(firstInvoiceItem);
    }
});