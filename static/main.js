// === MIZONA - JAVASCRIPT PRINCIPAL ===
document.addEventListener('DOMContentLoaded', function() {
    initSearch();
    initCart();
    initDashboard();
    setupModals();
});
///////////////////////////////////////////////////////////////////////////////////////////
// === BUSCADOR GLOBAL ===
function initSearch() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        // Ejecuta la búsqueda al presionar "Enter"
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchStores();
            }
        });
        
        // ¡SUPER MEJORA!: Busca automáticamente en tiempo real mientras el usuario escribe
        searchInput.addEventListener('input', searchStores);
    }
}

function searchStores() {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) return;

    const query = searchInput.value.toLowerCase().trim();
    const grid = document.getElementById('businessGrid');
    if (!grid) return;

    // Capturamos únicamente las tarjetas de negocio reales (.business-card)
    const stores = Array.from(grid.getElementsByClassName('business-card'));
    
    stores.forEach(store => {
        // Extraemos los textos de la tarjeta de forma segura
        const name = store.querySelector('h3')?.textContent.toLowerCase() || '';
        const locationText = store.querySelector('.location')?.textContent.toLowerCase() || '';
        // CORRECCIÓN: Capturamos el párrafo de la descripción (ej: "panadería", "mecánico")
        const description = store.querySelector('.card-body p')?.textContent.toLowerCase() || ''; 
        
        // Comprobamos si lo que escribió el usuario está en el nombre, la ciudad O la descripción/rubro
        if (name.includes(query) || locationText.includes(query) || description.includes(query)) {
            store.style.display = ""; // Muestra la tarjeta respetando tu CSS Grid profesional
        } else {
            store.style.display = "none"; // Oculta la tarjeta si no coincide
        }
    });
}
/////////////////////////////////////////////////////////////////////////////////////
// === CARRITO GLOBAL ===
let cart = JSON.parse(localStorage.getItem('mizona_cart')) || [];

function initCart() {
    updateCartDisplay();
}

function addToCart(productId, name, price) {
    const existing = cart.find(item => item.id === productId);
    if (existing) {
        existing.quantity += 1;
    } else {
        cart.push({ id: productId, name, price, quantity: 1 });
    }
    localStorage.setItem('mizona_cart', JSON.stringify(cart));
    updateCartDisplay();
    showNotification('Producto agregado al carrito ✅');
}

function updateCartDisplay() {
    const cartSection = document.getElementById('cartSection');
    const cartItems = document.getElementById('cartItems');
    const cartTotal = document.getElementById('cartTotal');
    
    if (cartSection && cartItems && cartTotal) {
        cartSection.style.display = cart.length ? 'block' : 'none';
        
        if (cart.length) {
            cartItems.innerHTML = cart.map(item => `
                <div class="cart-item">
                    <span>${item.name} <strong>x${item.quantity}</strong></span>
                    <span>Bs ${(item.price * item.quantity).toFixed(2)}</span>
                </div>
            `).join('');
            
            const total = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
            cartTotal.textContent = `Bs ${total.toFixed(2)}`;
        }
    }
}

function sendWhatsApp() {
    const storeId = window.location.pathname.split('/').pop();
    const products = cart.map(item => item.id);
    const quantities = cart.map(item => item.quantity);
    const total = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    
    const params = new URLSearchParams({
        'products[]': products,
        'quantities[]': quantities,
        total: total
    });
    
    window.location.href = `/whatsapp-order/${storeId}?${params}`;
}

// === DASHBOARD ===
function initDashboard() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', function() {
            document.querySelectorAll('.content-section').forEach(section => {
                section.classList.remove('active');
            });
            document.querySelectorAll('.nav-item').forEach(nav => {
                nav.classList.remove('active');
            });
            
            const sectionId = this.dataset.section;
            document.getElementById(sectionId)?.classList.add('active');
            this.classList.add('active');
        });
    });
}

let editProductId = null;

function showAddProductModal() {
    editProductId = null;
    document.getElementById('modalTitle').textContent = 'Nuevo Producto';
    document.getElementById('productForm').reset();
    document.getElementById('imagePreview').style.display = 'none';
    document.getElementById('productModal').style.display = 'block';
}

function showEditProductModal(productId) {
    editProductId = productId;
    // Cargar datos del producto via fetch('/api/products/' + productId)
    document.getElementById('modalTitle').textContent = 'Editar Producto';
    document.getElementById('productModal').style.display = 'block';
}

function closeProductModal() {
    document.getElementById('productModal').style.display = 'none';
}

function setupModals() {
    const modal = document.getElementById('productModal');
    if (modal) {
        window.onclick = function(event) {
            if (event.target === modal) {
                closeProductModal();
            }
        }
    }
    
    const form = document.getElementById('productForm');
    if (form) {
        form.onsubmit = handleProductForm;
        setupImageUpload();
    }
}

function setupImageUpload() {
    const uploadArea = document.getElementById('imageUpload');
    const fileInput = document.getElementById('productImage');
    const preview = document.getElementById('imagePreview');
    
    if (!uploadArea || !fileInput || !preview) return;
    
    uploadArea.addEventListener('click', () => fileInput.click());
    
    ['dragenter', 'dragover'].forEach(event => {
        uploadArea.addEventListener(event, () => uploadArea.classList.add('dragover'));
    });
    
    ['dragleave', 'drop'].forEach(event => {
        uploadArea.addEventListener(event, () => uploadArea.classList.remove('dragover'));
    });
    
    uploadArea.addEventListener('drop', e => {
        e.preventDefault();
        const files = e.dataTransfer.files;
        handleImageFile(files[0]);
    });
    
    fileInput.addEventListener('change', e => {
        handleImageFile(e.target.files[0]);
    });
    
    function handleImageFile(file) {
        if (file && file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = e => {
                preview.src = e.target.result;
                preview.style.display = 'block';
            };
            reader.readAsDataURL(file);
        }
    }
}

async function handleProductForm(e) {
    e.preventDefault();
    
    const formData = new FormData();
    formData.append('name', document.getElementById('productName').value);
    formData.append('price', document.getElementById('productPrice').value);
    formData.append('stock', document.getElementById('productStock').value);
    formData.append('description', document.getElementById('productDesc').value);
    
    const fileInput = document.getElementById('productImage');
    if (fileInput.files[0]) {
        formData.append('image', fileInput.files[0]);
    }
    
    const url = editProductId ? `/api/products/${editProductId}` : '/api/products';
    const method = editProductId ? 'PUT' : 'POST';
    
    try {
        const response = await fetch(url, {
            method: method,
            body: formData
        });
        
        if (response.ok) {
            showNotification('Producto guardado ✅');
            closeProductModal();
            location.reload(); // Recargar dashboard
        } else {
            const error = await response.json();
            showNotification('Error: ' + error.error, 'error');
        }
    } catch (error) {
        showNotification('Error de conexión', 'error');
    }
}

async function deleteProduct(productId) {
    if (confirm('¿Eliminar este producto?')) {
        try {
            const response = await fetch(`/api/products/${productId}`, { method: 'DELETE' });
            if (response.ok) {
                showNotification('Producto eliminado ✅');
                location.reload();
            }
        } catch (error) {
            showNotification('Error al eliminar', 'error');
        }
    }
}

// === UTILIDADES ===
function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `flash-message flash-${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 4000);
}

// Exponer funciones globales
window.searchStores = searchStores;
window.addToCart = addToCart;
window.sendWhatsApp = sendWhatsApp;
window.showAddProductModal = showAddProductModal;
window.closeProductModal = closeProductModal;
window.deleteProduct = deleteProduct;