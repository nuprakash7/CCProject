from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# SQLAlchemy Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    cart_items = db.relationship('CartItem', backref='user', lazy=True)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    product = db.relationship('Product', backref='cart_items')

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(255))

def insert_dummy_products():
    dummy_products = [
        {
            'name': 'Nintendo Switch',
            'description': 'The new Nintendo flagship!',
            'price': 399.99,
            'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/88/Nintendo-Switch-wJoyCons-BlRd-Standing-FL.jpg/300px-Nintendo-Switch-wJoyCons-BlRd-Standing-FL.jpg'
        },
        {
            'name': 'SG Cricket Bat',
            'description': 'Master-crafted English willow!',
            'price': 29.99,
            'image_url': 'https://shop.teamsg.in/cdn/shop/products/LIAM-XTREME-scaled.jpg?v=1696576680&width=1946'
        },
        {
            'name': 'Mountain Dew',
            'description': 'Darr ke aage jeet hai',
            'price': 3.99,
            'image_url': 'https://www.jiomart.com/images/product/original/491349790/mountain-dew-750-ml-product-images-o491349790-p491349790-0-202203150326.jpg'
        },
        {
            'name': 'RCB Jersey',
            'description': 'Not winning :(',
            'price': 19.99,
            'image_url': 'https://m.media-amazon.com/images/I/41g+pgWuaKL._AC_UY1100_.jpg'
        },
        {
            'name': 'Tender Coconut',
            'description': 'No one reads this',
            'price': 0.99,
            'image_url': 'https://m.media-amazon.com/images/I/81Tpge1r7SL.jpg'
        }
    ]

    for product_data in dummy_products:
        product = Product(**product_data)
        db.session.add(product)

    db.session.commit()


# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('register'))

        # Create a new user
        new_user = User(username=username, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# Route for logging in
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the username exists
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            # Set the username in the session
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('products'))

        flash('Invalid username or password. Please try again.', 'danger')
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/products')
def products():
    products = Product.query.all()
    return render_template('products.html', products=products)

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'username' not in session:
        flash('Please log in to add items to your cart.', 'warning')
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()
    product = Product.query.get_or_404(product_id)

    # Check if the product is already in the user's cart
    existing_cart_item = CartItem.query.filter_by(user_id=user.id, product_id=product.id).first()
    if existing_cart_item:
        existing_cart_item.quantity += 1
    else:
        new_cart_item = CartItem(user_id=user.id, product_id=product.id)
        db.session.add(new_cart_item)

    db.session.commit()
    flash(f'Added {product.name} to your cart.', 'success')
    return redirect(url_for('products'))


@app.route('/cart')
def view_cart():
    if 'username' not in session:
        flash('Please log in to view your cart.', 'warning')
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()
    cart_items = user.cart_items
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'username' not in session:
        flash('Please log in to proceed to checkout.', 'warning')
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()

    if request.method == 'POST':
        # Retrieve address and payment info from form
        address = request.form.get('address')
        payment_info = request.form.get('payment_info')

        # Update user's address in the database
        user.address = address
        db.session.commit()

        # Process the order (e.g., clear cart, create order record, etc.)
        clear_cart(user)
        flash('Order placed successfully!', 'success')
        return redirect(url_for('products'))

    return render_template('checkout.html')

def clear_cart(user):
    # Clear all cart items associated with the user
    CartItem.query.filter_by(user_id=user.id).delete()
    db.session.commit()



# Run the Flask app
if __name__ == '__main__':
    with app.app_context():
        
        # Create all database tables based on models
        db.create_all()
        #insert_dummy_products()
    app.run(debug=True)
