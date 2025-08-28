document.addEventListener('DOMContentLoaded', () => {
    // Referencias a elementos del DOM
    const voiceButton = document.getElementById('voice-button');
    const statusText = document.getElementById('status-text');
    const conversationLog = document.getElementById('conversation-log');
    const inventoryTableBody = document.getElementById('inventory-table-body');
    const searchInventoryInput = document.getElementById('search-inventory');
    const invoiceDisplay = document.getElementById('invoice-display');

    const assistantTab = new bootstrap.Tab(document.getElementById('asistente-nav-tab'));
    const billingTab = new bootstrap.Tab(document.getElementById('facturacion-nav-tab'));

    // Estado de la aplicación
    let isRecording = false;
    let conversationHistory = [];
    let allProducts = [];
    let currentInvoicePreview = null;
    let selectedVoice = null; // NUEVO: Variable para guardar la voz seleccionada

    // --- Configuración del Reconocimiento de Voz ---
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        statusText.textContent = "Tu navegador no soporta reconocimiento de voz.";
        voiceButton.disabled = true;
        return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = 'es-CO';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    // --- NUEVO: Cargar y seleccionar una voz ---
    function loadVoices() {
        const voices = window.speechSynthesis.getVoices();
        console.log("Voces disponibles:", voices); // Muestra todas las voces en la consola

        // Intenta encontrar una voz en español de alta calidad. Puedes cambiar este nombre.
        // Ejemplos: 'Google español', 'Microsoft Sabina - Spanish (Spain)', 'Paulina'
        selectedVoice = voices.find(voice => voice.name === 'Microsoft Sabina - Spanish (Spain)') ||
                        voices.find(voice => voice.lang.startsWith('es-ES')) ||
                        voices.find(voice => voice.lang.startsWith('es-MX')) ||
                        voices.find(voice => voice.lang.startsWith('es')); // La primera en español que encuentre

        if (selectedVoice) {
            console.log("Voz seleccionada:", selectedVoice.name);
        } else {
            console.log("No se encontró una voz preferida, se usará la voz por defecto.");
        }
    }

    // El listado de voces se carga de forma asíncrona.
    window.speechSynthesis.onvoiceschanged = loadVoices;
    loadVoices(); // Intenta cargar las voces al inicio

    // --- Funciones de la Interfaz ---

    const addMessageToLog = (text, sender) => {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);
        const p = document.createElement('p');
        p.textContent = text;
        messageDiv.appendChild(p);
        conversationLog.appendChild(messageDiv);
        conversationLog.scrollTop = conversationLog.scrollHeight;
    };

    const speak = (text) => {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);

        // Asigna la voz seleccionada si existe
        if (selectedVoice) {
            utterance.voice = selectedVoice;
        }

        utterance.lang = 'es-ES';
        utterance.rate = 1.1;
        window.speechSynthesis.speak(utterance);
    };

    const renderInventory = (products) => {
        inventoryTableBody.innerHTML = '';
        if (!products || products.length === 0) {
            inventoryTableBody.innerHTML = '<tr><td colspan="6" class="text-center">No hay productos.</td></tr>';
            return;
        }
        products.forEach(p => {
            const row = `
                <tr>
                    <td>${p.id}</td>
                    <td>${p.name}</td>
                    <td>${p.description || 'N/A'}</td>
                    <td>$${(p.sale_price || 0).toFixed(2)}</td>
                    <td>${p.quantity}</td>
                    <td>${p.location || 'N/A'}</td>
                </tr>
            `;
            inventoryTableBody.innerHTML += row;
        });
    };

    const renderInvoicePreview = (preview) => {
        currentInvoicePreview = preview;
        let itemsHtml = '';
        preview.items.forEach(item => {
            const itemTotal = item.quantity * item.unit_price;
            itemsHtml += `
    ${item.name.padEnd(30)} ${item.quantity.toString().padStart(4)}   $${item.unit_price.toFixed(2).padStart(8)}   $${itemTotal.toFixed(2).padStart(10)}
`;
        });

        const invoiceHtml = `
<div id="printable-invoice">
<pre>
------------------------------------------------------------
                 ** VISTA PREVIA DE FACTURA **
------------------------------------------------------------
Fecha: ${new Date(preview.created_at).toLocaleString()}

Cliente: ${preview.client_name}
Contacto: ${preview.client_contact || 'N/A'}
Email: ${preview.client_email || 'N/A'}
------------------------------------------------------------
Producto                       Cant.    P. Unit.        Total
------------------------------------------------------------
${itemsHtml}
------------------------------------------------------------
                                  Subtotal: $${preview.subtotal.toFixed(2).padStart(10)}
                                       IVA: $${preview.tax.toFixed(2).padStart(10)}
                                     TOTAL: $${preview.total.toFixed(2).padStart(10)}
------------------------------------------------------------
</pre>
</div>
<div class="mt-3 text-center">
    <button id="confirm-invoice-btn" class="btn btn-success me-2"><i class="fas fa-check-circle me-1"></i> Confirmar y Guardar</button>
    <button id="print-invoice-btn" class="btn btn-info me-2"><i class="fas fa-print me-1"></i> Imprimir</button>
    <button id="cancel-invoice-btn" class="btn btn-danger"><i class="fas fa-times-circle me-1"></i> Cancelar</button>
</div>
`;
        invoiceDisplay.innerHTML = invoiceHtml;
        billingTab.show();
        addInvoiceActionListeners();
    };

    const addInvoiceActionListeners = () => {
        document.getElementById('confirm-invoice-btn').addEventListener('click', confirmInvoice);
        document.getElementById('print-invoice-btn').addEventListener('click', printInvoice);
        document.getElementById('cancel-invoice-btn').addEventListener('click', cancelInvoice);
    };

    // --- Lógica de la Aplicación ---

    const fetchAllProducts = async () => {
        try {
            const response = await fetch('/api/products');
            if (!response.ok) throw new Error('Error al cargar productos');
            allProducts = await response.json();
            renderInventory(allProducts);
        } catch (error) {
            console.error(error);
            addMessageToLog("Error al cargar el inventario.", 'assistant');
        }
    };

    const processCommand = async (text) => {
        addMessageToLog(text, 'user');
        statusText.textContent = 'Procesando...';

        try {
            const response = await fetch('/api/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, history: conversationHistory })
            });

            if (!response.ok) throw new Error('Error en la respuesta del servidor.');

            const data = await response.json();
            const spokenResponse = data.spoken_response;

            addMessageToLog(spokenResponse, 'assistant');
            speak(spokenResponse);

            conversationHistory.push({ user: text, assistant: JSON.stringify(data.llm_response_json) });
            if (conversationHistory.length > 10) conversationHistory.shift();

            if (data.execution_result) {
                if (data.execution_result.products) {
                    renderInventory(data.execution_result.products);
                } else {
                    fetchAllProducts();
                }
                if (data.execution_result.invoice_preview) {
                    renderInvoicePreview(data.execution_result.invoice_preview);
                }
            }
        } catch (error) {
            console.error('Error:', error);
            const errorMsg = "Lo siento, hubo un error de comunicación.";
            addMessageToLog(errorMsg, 'assistant');
            speak(errorMsg);
        } finally {
            statusText.textContent = 'Presiona para hablar';
        }
    };

    const confirmInvoice = async () => {
        if (!currentInvoicePreview) return;
        try {
            const response = await fetch('/api/invoice/confirm', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(currentInvoicePreview)
            });
            const result = await response.json();
            if (result.status === 'success') {
                speak(result.message);
                addMessageToLog(result.message, 'assistant');
                fetchAllProducts();
                invoiceDisplay.innerHTML = `<p class="text-success text-center">${result.message}</p>`;
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            console.error('Error al confirmar factura:', error);
            const errorMsg = `Error al confirmar: ${error.message}`;
            speak(errorMsg);
            addMessageToLog(errorMsg, 'assistant');
        } finally {
            currentInvoicePreview = null;
        }
    };

    const printInvoice = () => {
        const printableContent = document.getElementById('printable-invoice').innerHTML;
        const printWindow = window.open('', '_blank');
        printWindow.document.write('<html><head><title>Factura</title></head><body>');
        printWindow.document.write(printableContent);
        printWindow.document.write('</body></html>');
        printWindow.document.close();
        printWindow.print();
    };

    const cancelInvoice = () => {
        currentInvoicePreview = null;
        invoiceDisplay.innerHTML = '<p class="text-muted">Aquí se mostrará la última factura generada por el asistente.</p>';
        const msg = "Operación cancelada.";
        addMessageToLog(msg, 'assistant');
        speak(msg);
        assistantTab.show();
    };

    // --- Event Listeners ---
    voiceButton.addEventListener('click', () => {
        window.speechSynthesis.cancel();
        if (isRecording) {
            recognition.stop();
        } else {
            recognition.start();
        }
    });

    recognition.onstart = () => {
        isRecording = true;
        voiceButton.classList.add('recording');
        statusText.textContent = 'Escuchando...';
    };
    recognition.onend = () => { isRecording = false; voiceButton.classList.remove('recording'); statusText.textContent = 'Presiona para hablar'; };
    recognition.onresult = (event) => { processCommand(event.results[0][0].transcript); };
    recognition.onerror = (event) => { console.error('Error de reconocimiento:', event.error); statusText.textContent = `Error: ${event.error}`; };

    searchInventoryInput.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        const filteredProducts = allProducts.filter(p =>
            p.name.toLowerCase().includes(searchTerm) ||
            (p.description && p.description.toLowerCase().includes(searchTerm))
        );
        renderInventory(filteredProducts);
    });

    // --- Inicialización ---
    fetchAllProducts();
});
