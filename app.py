import os
from flask_cors import CORS
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, jsonify
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user

load_dotenv()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
db = SQLAlchemy(app)
CORS(app)

# MODELS - ORM
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)

    # usuario pode adicionar produtos ao carrinho
    cart = db.relationship('CartItem', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'
    
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Product {self.name}>'
    

class CartItem(db.Model): 
    id = db.Column(db.Integer, primary_key=True)
    fk_user = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    fk_product = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<Cart {self.id}>'

# ROTAS
# autenticação
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['POST'])
def login():
    data = request.json

    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"message":"Dados inválidos"}), 400
    
    user = User.query.filter_by(username=data['username'], password=data['password']).first()

    if not user:
        return jsonify({"message":"Usuário ou senha inválidos"}), 401
    
    login_user(user)
    
    return jsonify({"message":"Login realizado com sucesso!"}), 200

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"message":"Logout realizado com sucesso!"}), 200

# gestão dos produtos
@app.route('/api/products/add', methods=['POST'])
@login_required
def add_product():
    
    data = request.json

    if not data or 'name' not in data or 'price' not in data:
        return jsonify({"message":"Dados inválidos"}), 400

    new_product = Product(
        name=data['name'],
        price=data['price'],
        description=data.get('description', "")
    )
    db.session.add(new_product)
    db.session.commit()

    return jsonify({"message":"Produto cadastrado com sucesso!"}), 201

@app.route('/api/products/delete/<int:product_id>', methods=['DELETE'])
@login_required
def delete_product(product_id):
    if not product_id:
        return jsonify({"message":"ID inválido"}), 400
    
    product = Product.query.get(product_id)

    if not product:
        return jsonify({"message":"Produto não encontrado"}), 404

    db.session.delete(product)
    db.session.commit()

    return jsonify({"message":"Produto excluído com sucesso!"}), 200

@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):

    if not product_id:
        return jsonify({"message":"ID inválido"}), 400
    
    product = Product.query.get(product_id)

    if not product:
        return jsonify({"message":"Produto não encontrado"}), 404

    return jsonify({"id":product_id,
                    "name":product.name,
                    "price":product.price,
                    "description":product.description}), 200

@app.route('/api/products/update/<int:product_id>', methods=['PUT'])
@login_required
def put_product(product_id):
    if not product_id:
        return jsonify({"message":"ID inválido"}), 400
    
    product = Product.query.get(product_id)

    if not product:
        return jsonify({"message":"Produto não encontrado"}), 404

    data = request.json

    product.name = data.get('name', product.name)
    product.price = data.get('price', product.price)
    product.description = data.get('description', product.description)

    db.session.commit()
    return jsonify({"message":"Produto excluído com sucesso!"}), 200

@app.route('/api/products', methods=['GET'])
def get_products():
    products = Product.query.all()

    list = []
    for product in products:
        list.append({
            "id": product.id,
            "name": product.name,
            "price": product.price
        })

    return jsonify(list), 200

# carrinho
@app.route('/api/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    request = request.json
    user = User.query.get(int(current_user.id))
    product = Product.query.get(product_id)
    qtd = request.get('quantity', 1)

    if not product:
        return jsonify({"message":"Produto não encontrado"}), 404

    cart = CartItem(
        fk_user=user.id,
        fk_product=product.id,
        quantity=qtd
    )

    db.session.add(cart)
    db.session.commit()
    
    return jsonify({"message":"Produto adicionado com sucesso"}), 200

@app.route('/api/cart/remove/<int:product_id>', methods=['POST'])
@login_required
def remove_from_cart(product_id):
    user = User.query.get(int(current_user.id))   
    cart = CartItem.query.filter_by(fk_user=user.id, fk_product=product_id).first()

    if not cart:
        return jsonify({"message":"Produto não encontrado no carrinho"}), 400

    db.session.delete(cart)
    db.session.commit()
    
    return jsonify({"message":"Produto removido com sucesso"}), 200

@app.route('/api/cart', methods=['GET'])
@login_required
def get_cart():
    user = User.query.get(int(current_user.id))
    cart_items = user.cart # substitui o filtro por fk_user

    if not cart_items:
        return jsonify({"message":"Carrinho vazio"}), 200
    
    cart = []

    for item in cart_items:
        product = Product.query.get(item.fk_product)
        cart.append({
            "id": item.id,
            "product_id": item.fk_product,
            "name": product.name,
            "price": product.price,
            "quantity": item.quantity
        })

    return jsonify(cart), 200

@app.route('/api/cart/checkout', methods=['GET'])
@login_required
def checkout():
    user = User.query.get(int(current_user.id))    
    cart_items = user.cart # substitui o filtro por fk_user usando relationship

    for item in cart_items:
        db.session.delete(item)
    db.session.commit()

    return jsonify({"message":"Checkout realizada com sucesso!"}), 200

# teste
@app.route('/teste')
def hello_world():
    return 'Hello, World!'

if __name__ == '__main__':
    app.run(debug=True, host=os.getenv('HOST'), port=os.getenv('PORT'))