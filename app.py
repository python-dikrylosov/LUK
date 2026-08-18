import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# --- Конфигурация ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-me'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Инициализация ---
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# --- Проверка и создание папок и файлов ---
def init_directories_and_files():
    # Папки
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('uploads', exist_ok=True)

    # Шаблоны
    templates_needed = {
        'index.html': '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Магазин</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <h1>Добро пожаловать в наш магазин!</h1>
    {% if current_user.is_authenticated %}
        <p>Привет, {{ current_user.username }}! <a href="{{ url_for('logout') }}">Выйти</a></p>
    {% else %}
        <a href="{{ url_for('login') }}">Войти</a> | <a href="{{ url_for('register') }}">Регистрация</a>
    {% endif %}
    <hr>
    <h2>Товары:</h2>
    {% for product in products %}
        <div>
            <h3>{{ product.name }}</h3>
            <p>{{ product.description }}</p>
            <p>{{ product.price }} руб.</p>
            <button onclick="addToCart({{ product.id }})">В корзину</button>
        </div>
    {% endfor %}
    <hr>
    <a href="{{ url_for('cart') }}">Корзина ({{ session.get('cart_count', 0) }})</a>
    <script>
        function addToCart(productId) {
            fetch('/cart/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({product_id: productId})
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'added') {
                    alert('Добавлено в корзину!');
                    location.reload();
                }
            });
        }
    </script>
</body>
</html>''',

        'login.html': '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Вход</title>
</head>
<body>
    <h2>Вход</h2>
    <form method="POST">
        <input type="text" name="username" placeholder="Логин" required><br>
        <input type="password" name="password" placeholder="Пароль" required><br>
        <button type="submit">Войти</button>
    </form>
    <a href="{{ url_for('register') }}">Регистрация</a>
</body>
</html>''',

        'register.html': '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Регистрация</title>
</head>
<body>
    <h2>Регистрация</h2>
    <form method="POST">
        <input type="text" name="username" placeholder="Логин" required><br>
        <input type="text" name="phone" placeholder="Телефон" required><br>
        <input type="password" name="password" placeholder="Пароль" required><br>
        <button type="submit">Зарегистрироваться</button>
    </form>
    <a href="{{ url_for('login') }}">Вход</a>
</body>
</html>''',

        'cart.html': '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Корзина</title>
</head>
<body>
    <h2>Корзина</h2>
    {% if cart_items %}
        {% for item in cart_items %}
            <div>{{ item.product.name }} x{{ item.quantity }}</div>
        {% endfor %}
        <p>Итого: {{ total_price }} руб.</p>

        {% if current_user.is_authenticated %}
            <a href="{{ url_for('checkout') }}">Оформить заказ</a>
        {% else %}
            <p><a href="{{ url_for('login') }}">Войдите</a>, чтобы оформить заказ</p>
            <form method="POST" action="{{ url_for('checkout') }}">
                <input type="text" name="phone" placeholder="Телефон для заказа" required>
                <button type="submit">Заказать по телефону</button>
            </form>
        {% endif %}
    {% else %}
        <p>Корзина пуста</p>
    {% endif %}
    <a href="{{ url_for('index') }}">Назад</a>
</body>
</html>''',

        'checkout.html': '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Оформление заказа</title>
</head>
<body>
    <h2>Оформление заказа</h2>
    <p>Итого: {{ total_price }} руб.</p>
    <form method="POST">
        <input type="text" name="phone" placeholder="Ваш телефон" required>
        <button type="submit">Подтвердить заказ</button>
    </form>
    <a href="{{ url_for('cart') }}">Назад</a>
</body>
</html>'''
    }

    for filename, content in templates_needed.items():
        path = os.path.join('templates', filename)
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Создан шаблон: {path}")

    # Стили
    style_path = os.path.join('static', 'style.css')
    if not os.path.exists(style_path):
        with open(style_path, 'w', encoding='utf-8') as f:
            f.write('''body { font-family: Arial; margin: 40px; }''')
        print(f"Создан файл стилей: {style_path}")


# --- Модели ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    is_manager = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    category = db.Column(db.String(100))


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer, default=1)
    product = db.relationship('Product')


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    total_price = db.Column(db.Float)
    status = db.Column(db.String(50), default='pending')
    payment_method = db.Column(db.String(50), default='phone_order')
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- Маршруты ---
@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Неверный логин или пароль')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        phone = request.form['phone']
        password = request.form['password']
        user = User(username=username, phone=phone)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Регистрация успешна!')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/cart')
def cart():
    if current_user.is_authenticated:
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    else:
        cart_item_ids = session.get('cart', [])
        from collections import Counter
        counts = Counter(cart_item_ids)
        cart_items = []
        for pid, qty in counts.items():
            prod = Product.query.get(pid)
            if prod:
                cart_items.append(type('obj', (object,), {'product': prod, 'quantity': qty})())
    total_price = sum(item.product.price * item.quantity for item in cart_items)
    session['cart_count'] = len(cart_item_ids) if not current_user.is_authenticated else len(cart_items)
    return render_template('cart.html', cart_items=cart_items, total_price=total_price)


@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    product_id = request.json['product_id']
    if current_user.is_authenticated:
        item = CartItem(user_id=current_user.id, product_id=product_id, quantity=1)
        db.session.add(item)
    else:
        cart = session.get('cart', [])
        cart.append(product_id)
        session['cart'] = cart
    db.session.commit()
    return jsonify({'status': 'added'})


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        phone = request.form['phone']
        if current_user.is_authenticated:
            cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
            total = sum(item.product.price * item.quantity for item in cart_items)
            order = Order(user_id=current_user.id, total_price=total, payment_method='phone_order', phone=phone)
            db.session.add(order)
            for item in cart_items:
                db.session.delete(item)
        else:
            cart_item_ids = session.get('cart', [])
            products = [Product.query.get(pid) for pid in cart_item_ids if Product.query.get(pid)]
            total = sum(p.price for p in products)
            order = Order(total_price=total, payment_method='phone_order', phone=phone)
            db.session.add(order)
            session.pop('cart', None)
        db.session.commit()
        flash('Заказ оформлен!')
        return redirect(url_for('index'))

    cart_items = session.get('cart', [])
    products = [Product.query.get(pid) for pid in cart_item_ids if Product.query.get(pid)]
    total_price = sum(p.price for p in products)
    return render_template('checkout.html', total_price=total_price)


# --- Инициализация БД ---
def init_db():
    db.create_all()
    if Product.query.count() == 0:
        sample_products = [
            Product(name="Аккумулятор 6CT-100", price=5000.0, description="Для трактора МТЗ", category="Аккумуляторы"),
            Product(name="Свечи зажигания", price=350.0, description="Высокое качество", category="Запчасти"),
            Product(name="Фильтр масляный", price=200.0, description="Для двигателя ЯМЗ", category="Фильтры")
        ]
        for p in sample_products:
            db.session.add(p)
        db.session.commit()
        print("Добавлены тестовые товары.")


if __name__ == '__main__':
    init_directories_and_files()
    with app.app_context():
        init_db()
    app.run(host='0.0.0.0', port=8000, debug=True)
