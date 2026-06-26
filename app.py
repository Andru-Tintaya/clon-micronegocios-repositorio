from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import supabase
import os
from datetime import datetime
import uuid
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'mizona-dev-secret-key')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

supabase_client = supabase.create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def vendedor_required(f):
    def wrap(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'vendedor':
            flash('Acceso restringido', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

@app.route('/')
def index():
    stores = supabase_client.table('stores').select("*").limit(12).execute().data or []
    return render_template('index.html', stores=stores)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            data = request.form
            password_hash = generate_password_hash(data['password'])
            
            user_result = supabase_client.table('users').insert({
                'email': data['email'],
                'whatsapp': data['whatsapp'],
                'password_hash': password_hash,
                'full_name': data['full_name'],
                'role': 'vendedor'
            }).execute()
            
            user_id = user_result.data[0]['id']
            
            supabase_client.table('stores').insert({
                'user_id': user_id,
                'name': data['business_name'],
                'description': data.get('description', ''),
                'whatsapp': data['whatsapp'],
                'city': data['city']
            }).execute()
            
            flash('¡Registro exitoso! Inicia sesión.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['identifier'].strip()
        password = request.form['password']
        
        try:
            users = supabase_client.table('users').select("*").or_(
                f"email.eq.{identifier},whatsapp.eq.{identifier}"
            ).execute().data
            
            if users and check_password_hash(users[0]['password_hash'], password):
                session['user_id'] = users[0]['id']
                session['role'] = users[0]['role']
                session['full_name'] = users[0]['full_name']
                flash('¡Bienvenido!', 'success')
                return redirect(url_for('dashboard'))
            flash('Credenciales incorrectas', 'error')
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@vendedor_required
def dashboard():
    store_result = supabase_client.table('stores').select("*").eq('user_id', session['user_id']).execute()
    store = store_result.data[0] if store_result.data else None
    
    products_result = supabase_client.table('products').select("*").eq('store_id', store['id']).execute()
    products = products_result.data if products_result.data else []
    
    return render_template('dashboard.html', store=store, products=products)

@app.route('/tienda/<store_id>')
def tienda(store_id):
    store_result = supabase_client.table('stores').select("*").eq('id', store_id).execute()
    store = store_result.data[0] if store_result.data else None
    
    if not store:
        flash('Tienda no encontrada')
        return redirect(url_for('index'))
    
    products_result = supabase_client.table('products').select("*").eq('store_id', store_id).execute()
    products = products_result.data if products_result.data else []
    
    return render_template('tienda.html', store=store, products=products)

# ✅ FIXED: API PRODUCTOS
@app.route('/api/products', methods=['POST'])
@vendedor_required
def add_product():
    try:
        print("📤 Nueva producto...")
        
        # Store ID
        store_result = supabase_client.table('stores').select('id').eq('user_id', session['user_id']).execute()
        store_id = store_result.data[0]['id']
        
        # IMAGEN ✅ FIXED
        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                print(f"📸 Procesando {file.filename}...")
                file_ext = file.filename.rsplit('.', 1)[1].lower()
                file_name = f"{uuid.uuid4()}.{file_ext}"
                file_path = f"products/{store_id}/{file_name}"
                
                # Upload
                upload_result = supabase_client.storage.from_('product-images').upload(file_path, file.read())
                
                if upload_result:
                    # ✅ FIXED: Manejo universal de get_public_url
                    public_url = supabase_client.storage.from_('product-images').get_public_url(file_path)
                    
                    if isinstance(public_url, dict):
                        image_url = public_url.get('publicUrl') or public_url.get('data', [{}])[0].get('publicUrl')
                    else:
                        image_url = str(public_url)
                    
                    print(f"✅ Imagen OK: {image_url[:50]}...")
                else:
                    print("⚠️ Upload falló, sin imagen")
        
        # Producto
        product_data = {
            'store_id': store_id,
            'name': request.form['name'],
            'price': float(request.form['price']),
            'description': request.form.get('description', ''),
            'stock': int(request.form['stock']),
            'image_url': image_url
        }
        
        result = supabase_client.table('products').insert(product_data).execute()
        print("✅ Producto guardado!")
        
        return jsonify({
            'success': True,
            'image_url': image_url,
            'product': result.data[0]
        }), 201
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400
# ✅ FIXED: DELETE PRODUCTOS
@app.route('/api/products/<product_id>', methods=['DELETE'])
@vendedor_required
def delete_product(product_id):
    try:
        print(f"🗑️ Borrando producto {product_id}")
        
        # Verificar permiso
        product_result = supabase_client.table('products').select('store_id').eq('id', product_id).execute()
        if not product_result.data:
            return jsonify({'error': 'Producto no encontrado'}), 404
        
        product_store_id = product_result.data[0]['store_id']
        user_store_result = supabase_client.table('stores').select('id').eq('user_id', session['user_id']).execute()
        user_store_id = user_store_result.data[0]['id']
        
        if product_store_id != user_store_id:
            return jsonify({'error': 'No autorizado'}), 403
        
        # Borrar
        supabase_client.table('products').delete().eq('id', product_id).execute()
        print("✅ Producto borrado!")
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"❌ Error delete: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/products/<product_id>', methods=['PUT'])
@vendedor_required
def update_product(product_id):
    try:
        # Similar a add_product pero UPDATE
        store_result = supabase_client.table('stores').select('id').eq('user_id', session['user_id']).execute()
        store_id = store_result.data[0]['id']
        
        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                file_ext = file.filename.rsplit('.', 1)[1].lower()
                file_name = f"{uuid.uuid4()}.{file_ext}"
                file_path = f"products/{store_id}/{file_name}"
                
                supabase_client.storage.from_('product-images').upload(file_path, file.read())
                public_url_result = supabase_client.storage.from_('product-images').get_public_url(file_path)
                image_url = public_url_result.get('publicUrl', None)
        
        update_data = {
            'name': request.form['name'],
            'price': float(request.form['price']),
            'description': request.form.get('description', ''),
            'stock': int(request.form['stock'])
        }
        if image_url:
            update_data['image_url'] = image_url
        
        result = supabase_client.table('products').update(update_data).eq('id', product_id).execute()
        return jsonify(result.data[0])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/whatsapp-order/<store_id>')
def whatsapp_order(store_id):
    products = request.args.getlist('products[]')
    quantities = request.args.getlist('quantities[]')
    total = float(request.args.get('total', 0))
    
    store = supabase_client.table('stores').select('name,whatsapp').eq('id', store_id).execute().data[0]
    
    message = f"🛒 *PEDIDO MiZona*\n\n🏪 {store['name']}\n\n"
    total_real = 0
    for i, (pid, qty) in enumerate(zip(products, quantities)):
        if pid:
            product = supabase_client.table('products').select('name,price').eq('id', pid).execute().data[0]
            subtotal = product['price'] * int(qty)
            total_real += subtotal
            message += f"{i+1}. {product['name']} x{qty} = Bs {subtotal:.2f}\n"
    
    message += f"\n💰 *TOTAL: Bs {total_real:.2f}*"
    
    whatsapp_url = f"https://wa.me/{store['whatsapp'].replace('+', '')}?text={message.replace(' ', '%20').replace('\n', '%0A')}"
    return redirect(whatsapp_url)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5003)