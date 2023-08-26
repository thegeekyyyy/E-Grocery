from flask import (Flask, render_template, request, redirect, send_file, url_for, session, flash, make_response)
from flask_sqlalchemy import SQLAlchemy
from jinja2 import Template
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask import app
from flask import jsonify
from sqlalchemy import or_, func
import os
import csv


app = Flask(__name__)
app.config["SECRET_KEY"] = "your_secret_key_here"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.sqlite3"  # database file path
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['CSV_FOLDER'] = 'csv'

db = SQLAlchemy(app)
app.app_context().push()
db.create_all()
# db.init_app(app)

class User(db.Model, UserMixin):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    userrole = db.Column(db.String(255), nullable=False, default="User")
    created_at = db.Column(db.DateTime, default=datetime.now())

class Categories(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    categoryname = db.Column(db.String(255), nullable=False)

class Product(db.Model):
    __tablename__ = "product"
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    productname = db.Column(db.String(255))
    price = db.Column(db.Float)
    original_quantity = db.Column(db.Integer)
    quantity = db.Column(db.Integer)
    unit = db.Column(db.String(255))

    category = db.relationship('Categories', backref=db.backref('products', lazy=True))

class Cart(db.Model):
    __tablename__ = "cart"
    id = db.Column(db.Integer, primary_key = True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable =False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quantity = db.Column(db.Integer)
    price = db.Column(db.Integer)
    total = db.Column(db.Integer)

    product = db.relationship('Product', backref=db.backref('carts', lazy=True))

class Order(db.Model):
    __tablename__ = "order"
    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantitybrought = db.Column(db.Integer)

# @app.route('/xyz')
# def xyz():
#     engine = db.engine
#     db.create_all()

# @app.route("/xyz")
# def xyz():
#     engine = db.engine
#     Categories.__table__.drop(engine)


@app.route('/search', methods=["GET"])
def search():
    query = request.args.get('query', '')
    user_id = session.get('user_id')
    categories = Categories.query.all()

    if query:
        # Filter products based on the search query (case-insensitive)
        filtered_products = Product.query.join(Categories).filter(
            or_(
                func.lower(Product.productname).like(f'%{query.lower()}%'),
                func.lower(Categories.categoryname).like(f'%{query.lower()}%'),
                Product.price.like(f'%{query}%')
            )
        ).all()
    else:
        # If no query is provided, show all products
        filtered_products = Product.query.all()

    return render_template('search_results.html', filtered_products=filtered_products, user_id=user_id, categories=categories)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password, method="sha256")
        new_user = User(
            username=username,
            password=hashed_password,
        )
        db.session.add(new_user)
        db.session.commit()
        flash("You have successfully registered.","success")
        return redirect(url_for("login"))
    else:
        return render_template("register.html")
    
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        usserole = request.form["userrole"]
        user = User.query.filter_by(username=username).first()
        if user:
            if check_password_hash(user.password, password):
                session["user_id"] = user.id
                session["username"] = user.username
                session["userrole"] = user.userrole
                
                if user.userrole == "User":
                    flash('You have successfully logged in.', 'success')
                    return redirect(url_for("user_dashboard"))
                elif user.userrole == "Manager":
                    flash('You have successfully logged in.', 'success')
                    return redirect(url_for("manager_dashboard"))
            else:
                flash( 'Incorrect password!', 'error')
                return render_template("login.html")
        else:
            flash( 'User does not exist!', 'error')
            return render_template("login.html")
    else:
        return render_template("login.html")

@app.route('/manager_dashboard', methods=["GET", "POST"])
def manager_dashboard():
    username = session.get('username')
    existing_categories = Categories.query.all()  # Fetch all existing categories from the database
    if request.method == "POST":
        categoryname = request.form.get('categoryname')
        print("Category name received:", categoryname) 
        if categoryname:
            existing_category = Categories.query.filter_by(categoryname=categoryname).first()
            if existing_category:
                flash("Category already exists.", "error")
            else:
                new_category = Categories(categoryname=categoryname)
                db.session.add(new_category)
                db.session.commit()
                flash("You have successfully added the category.", "success")
                # Update the existing_categories list to include the newly added category
                existing_categories.append(new_category)
        elif 'productname' in request.form:  # Check if product form is submitted
            productname = request.form['productname']
            unit = request.form['unit']
            rateperunit = request.form['rateperunit']
            original_quantity = request.form['quantity']
            quantity = request.form['quantity']
            category_id = request.form['category_id']
            if productname and unit and rateperunit and quantity and category_id:
            # if productname and unit and rateperunit and quantity:
                new_product = Product(
                    productname=productname,
                    unit = unit,
                    price=int(rateperunit),
                    original_quantity=int(original_quantity),
                    quantity=int(quantity),
                    category_id=int(category_id)
                )
                db.session.add(new_product)
                db.session.commit()
                flash("You have successfully added the product.", "success")
            else:
                flash("Product details were not provided.", "error")
        else:
            flash("Category name was not provided.", "error")
        return redirect(url_for("manager_dashboard")) 
    return render_template("manager_dashboard.html", username=username, existing_categories=existing_categories)

@app.route('/summary')
def summary():
    products = Product.query.all()
    categories = Categories.query.all()
    orders = Order.query.all()
    
    # Collect product sold data by category
    product_sold_data = []

    for category in categories:
        products_in_category = Product.query.filter_by(category_id=category.id).all()
        quantity_sold = sum([product.original_quantity - product.quantity for product in products_in_category])
        product_sold_data.append(quantity_sold)
    category_names = [category.categoryname for category in categories]

    # # Collect top selling products data
    top_selling_products_data = []

    for product in products:
        sold_quantity = product.original_quantity - product.quantity
        top_selling_products_data.append((product.productname, sold_quantity))

    top_selling_products_data.sort(key=lambda x: x[1], reverse=True)
    top_selling_products = top_selling_products_data[:10]
    
    kwargs = {
        'product_sold': {
            'labels': category_names,
            'data': product_sold_data
        },
        'top_selling_products': {
            'labels': [product[0] for product in top_selling_products],
            'data': [product[1] for product in top_selling_products]
        }
    }

    print("Response Data:", kwargs)
    return render_template('summary.html', kwargs = kwargs)

@app.route('/export')
def export():
    users= User.query.all()
    products= Product.query.all()
    categories= Categories.query.all()
    orders = Order.query.all()

    # if csv folder does not exist, create it
    if not os.path.exists(app.config['CSV_FOLDER']):
        os.makedirs(app.config['CSV_FOLDER'])
    else:
        # remove earlier zip files
        for file in os.listdir(app.config['CSV_FOLDER']):
            if file.endswith('.zip'):
                os.remove(os.path.join(app.config['CSV_FOLDER'], file))

    filenames = ['users.csv', 'products.csv', 'categories.csv', 'orders.csv']

    # create csv files for each table
    with open(os.path.join(app.config['CSV_FOLDER'], 'users.csv'), 'w') as f:
        csvwriter = csv.writer(f)
        csvwriter.writerow(['id', 'username', 'password', 'userrole'])
        for user in users:
            csvwriter.writerow([user.id, user.username, user.password, user.userrole])

    with open(os.path.join(app.config['CSV_FOLDER'], 'products.csv'), 'w') as f:
        csvwriter = csv.writer(f)
        csvwriter.writerow(['id', 'category_id', 'productname', 'price', 'original_quanity', 'quantity', 'unit'])
        for product in products:
            csvwriter.writerow([product.id, product.category_id, product.productname, product.price, product.original_quantity, product.quantity, product.unit])

    with open(os.path.join(app.config['CSV_FOLDER'], 'categories.csv'), 'w') as f:
        csvwriter = csv.writer(f)
        csvwriter.writerow(['id', 'categoryname'])
        for category in categories:
            csvwriter.writerow([category.id, category.categoryname])

    with open(os.path.join(app.config['CSV_FOLDER'], 'orders.csv'), 'w') as f:
        csvwriter = csv.writer(f)
        csvwriter.writerow(['id', 'user_id', 'product_id'])
        for order in orders:
            csvwriter.writerow([order.id, order.user_id, order.product_id])

    # zip the files and return the zip file
    import zipfile
    zipfilename = f'csv_{datetime.now().strftime("%Y%m%d%H%M%S")}.zip'
    zipfilepath = os.path.join(app.config['CSV_FOLDER'], zipfilename)
    with zipfile.ZipFile(zipfilepath, 'w') as zip:
        for filename in filenames:
            path = os.path.join(app.config['CSV_FOLDER'], filename)
            zip.write(path, arcname=filename)
            os.remove(path)

    return send_file(zipfilepath, as_attachment=True)

@app.route('/edit_category/<int:category_id>', methods=['GET', 'POST'])
def edit_category(category_id):
    if request.method == 'POST':
        updatecategoryname = request.form['updatecategoryname']
        db.session.query(Categories).filter(Categories.id == category_id).update({Categories.categoryname: updatecategoryname})
        db.session.commit()
        flash("You have successfully updated the category.", "success")
        return redirect(url_for('manager_dashboard'))
    return redirect(url_for('manager_dashboard'))

@app.route('/delete_category/<int:category_id>', methods=['GET', 'POST'])
def delete_category(category_id):
    if request.method=='GET':
        products = Product.query.filter(Product.category_id == category_id)
        for product in products:
            db.session.delete(product)
        db.session.commit()
        delcat = Categories.query.filter(Categories.id == category_id).one()
        db.session.delete(delcat)
        db.session.commit()
    return redirect(url_for('manager_dashboard'))

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if request.method == 'POST':
        updateproductname = request.form['updateproductname']
        updateunit = request.form['updateunit']
        updaterateperunit = float(request.form['updaterateperunit'])  
        updatequantity = int(request.form['updatequantity'])
        product = Product.query.get(product_id)
        if product:
            product.productname = updateproductname
            product.unit = updateunit
            product.price = updaterateperunit
            product.quantity = updatequantity
            db.session.commit()
            flash("You have successfully updated the product.", "success")
            return redirect(url_for('manager_dashboard'))
        else:
            flash("Product not found.", "error")
            return redirect(url_for('manager_dashboard'))
    return redirect(url_for('manager_dashboard'))

@app.route('/delete_product/<int:product_id>', methods=['GET','POST'])
def delete_product(product_id):
    if request.method=='GET':
        delprod = Product.query.filter(Product.id == product_id).one()
        db.session.delete(delprod)
        db.session.commit()
    return redirect(url_for('manager_dashboard'))

@app.route('/user_dashboard', methods=["GET", "POST"])
def user_dashboard():
    username = session.get('username')
    user_id = session.get('user_id')
    existing_categories = Categories.query.all()
    products = Product.query.all()

    available_quantity = None

    if request.method == "POST":
        quantity = int(request.form['productquantity'])
        price = int(request.form['productprice'])
        total = int(request.form['totalprice'])
        product_id = int(request.form['product_id'])
        user_id = int(request.form['user_id'])

        # Fetch the product's available quantity from the database
        product = Product.query.get(product_id)
        available_quantity = product.quantity

        if quantity <= available_quantity:
            addtocartitem = Cart(
                quantity=quantity,
                price=price,
                total=total,
                product_id=product_id,
                user_id=user_id
            )
            db.session.add(addtocartitem)
            db.session.commit()
            flash("Product successfully added.", "success")
        else:
            flash(f"Please enter quantity less than {available_quantity}.", "danger")
    return render_template("user_dashboard.html", username=username, existing_categories=existing_categories, user_id=user_id, products=products, available_quantity = available_quantity)

@app.route('/cart/<int:user_id>', methods=["GET", "POST"])
def cart(user_id):
    username = session.get('username')
    # cartitems = Cart.query.all()
    cartitems = Cart.query.filter(Cart.user_id == user_id)
    product = Product.query.all()
    grand_total = sum(item.total for item in cartitems)
    return render_template("cart.html", username = username, cartitems = cartitems, grand_total=grand_total, user_id = user_id, product = product)

@app.route('/delete_cartitem/<int:cart_id>', methods=['GET','POST'])
def delete_cartitem(cart_id):
    if request.method=='GET':
        delcartitem = Cart.query.filter(Cart.id == cart_id).one()
        db.session.delete(delcartitem)
        db.session.commit()
    return redirect(url_for('cart', user_id=session.get('user_id')))

@app.route('/buyall/<int:user_id>', methods=["GET", "POST"])
def buyall(user_id):
    if request.method=='POST':
        cart_items = Cart.query.filter_by(user_id=user_id).all()
        for cart_item in cart_items:
            order = Order(user_id=user_id, product_id=cart_item.product_id, quantitybrought=cart_item.quantity)
            db.session.add(order)

            product = Product.query.get(cart_item.product_id)
            product.quantity -= cart_item.quantity
            db.session.add(product)
        db.session.commit()
        Cart.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        flash("You have successfully purchased the products.", "success")
        return redirect(url_for('user_dashboard'))
    cart_items = Cart.query.filter_by(user_id=user_id).all()
    return render_template('cart.html', cartitems=cart_items, user_id=user_id)

@app.route('/edit_cartitem/<int:cart_id>', methods=["GET", "POST"])
def edit_cartitem(cart_id):
    if request.method == 'POST':  
        updatequantity = int(request.form['updatequantity'])
        updatetotal = int(request.form['updatetotal'])
        
        cartitem = Cart.query.get(cart_id)
        
        if cartitem:
            product = Product.query.get(cartitem.product_id)  # Fetch the product associated with the cart item
            available_quantity = product.quantity

            if updatequantity <= available_quantity:
                db.session.query(Cart).filter(Cart.id == cart_id).update({Cart.quantity: updatequantity, Cart.total: updatetotal})
                db.session.commit()
                flash("You have successfully updated the cart item.", "success")
            else:
                flash(f"Please enter quantity less than {available_quantity}.", "danger")
        else:
            flash("Cart item not found.", "error")
        
        return redirect(url_for("cart", user_id=session.get('user_id')))
    
    return redirect(url_for("cart", user_id=session.get('user_id')))
    
@app.route('/order/<int:user_id>', methods=["GET", "POST"])
def order(user_id):
    username = session.get('username')
    user_orders = Order.query.filter(Order.user_id == user_id).all()

    if user_orders:
        orders = []
        for order in user_orders:
            product = Product.query.get(order.product_id)
            orders.append({"order": order, "product": product})

        return render_template("order.html", username=username, user_id=user_id, orders=orders)
    else:
        flash("You have not purchased any products yet.", "error")
        return render_template("order.html", username=username, user_id=user_id, orders=[])

@app.route("/logout")
def logout():   
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)