from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from unicodedata import category
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta



UPLOAD_FOLDER = r'C:\Users\kashi\OneDrive\Desktop\OurProject\static\image'  # Your upload folder path
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.secret_key = '1234'

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@localhost/Project'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db = SQLAlchemy(app)


# Models
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    contact_number = db.Column(db.String(15))
    is_admin = db.Column(db.Boolean, default=False)

class Location(db.Model):
    __tablename__ = 'locations'
    id = db.Column(db.Integer, primary_key=True)
    city_name = db.Column(db.String(50), nullable=False)

class Restaurant(db.Model):
    __tablename__ = 'restaurants'
    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    restaurant_name = db.Column(db.String(100), nullable=False)
    cuisine = db.Column(db.String(100))
    distance = db.Column(db.Float, default=0.0)
    rating = db.Column(db.Float, default=0.0)
    image_url = db.Column(db.String(255), default='static/default.jpg')

    # Add retailer_id to associate a restaurant with a retailer
    retailer_id = db.Column(db.Integer, db.ForeignKey('retailers.id'), nullable=True)


class Dish(db.Model):
    __tablename__ = 'dishes'
    id = db.Column(db.Integer, primary_key=True)
    dish_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(250),nullable=False)
    price = db.Column(db.Float, default=200)
    category = db.Column(db.String(100),nullable=False)
    image_url = db.Column(db.String(255), default='static/default.jpg')
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    restaurant = db.relationship('Restaurant', backref=db.backref('dishes', lazy=True))

    # Add retailer_id to associate each dish with a retailer
    retailer_id = db.Column(db.Integer, db.ForeignKey('retailers.id'), nullable=False)

class Retailer(db.Model):
    __tablename__ = 'retailers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    contact_number = db.Column(db.String(15), nullable=False)
    address = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    registration_date = db.Column(db.DateTime, default=db.func.now())
    is_active = db.Column(db.Boolean, default=True)

class Cart(db.Model):
    __tablename__ = 'cart'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Links to the User
    dish_id = db.Column(db.Integer, db.ForeignKey('dishes.id'), nullable=False)  # Links to the Dish
    quantity = db.Column(db.Integer, default=1, nullable=False)  # Tracks the quantity of each dish

    # Relationships
    user = db.relationship('User', backref=db.backref('cart_items', lazy=True))
    dish = db.relationship('Dish', backref=db.backref('in_carts', lazy=True))

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(50), default='Pending')  # Order status: Pending, Delivered, etc.
    created_at = db.Column(db.DateTime, default=db.func.now())  # Timestamp for order creation
    delivery_time = db.Column(db.DateTime)  # Time when the order is expected to be delivered

    # Relationships
    user = db.relationship('User', backref=db.backref('orders', lazy=True))


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    dish_id = db.Column(db.Integer, db.ForeignKey('dishes.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    # Relationships
    order = db.relationship('Order', backref=db.backref('order_items', lazy=True))
    dish = db.relationship('Dish', backref=db.backref('ordered_items', lazy=True))


# Routes
@app.route('/')
def home():
    # Fetch all locations for the dropdown
    locations = Location.query.all()

    # Get the selected location from the query parameter (default to "India")
    selected_location_id = request.args.get('location_id', type=int)
    if selected_location_id:
        selected_location = Location.query.get_or_404(selected_location_id)
        restaurants = Restaurant.query.filter_by(location_id=selected_location_id).all()
    else:
        selected_location = {"city_name": "India"}  # Default value
        restaurants = Restaurant.query.all()

    return render_template(
        'home.html',
        locations=locations,
        selected_location=selected_location,
        restaurant=restaurants
    )


# Route to handle search suggestions
@app.route('/search_suggestions')
def search_suggestions():
    query = request.args.get('q', '').lower()
    suggestions = []

    if query:
        # Query your database to get suggestions based on dish name
        dishes = Dish.query.filter(Dish.name.ilike(f'%{query}%')).limit(5).all()  # Assuming 'Dish' is your model
        for dish in dishes:
            suggestions.append({"name": dish.name})  # Send dish name as suggestion

    return jsonify({"suggestions": suggestions})


# Route to handle search results
@app.route('/search_results')
def search_results():
    query = request.args.get('q', '').lower()
    results = []

    if query:
        # Query your database to get results based on dish name
        dishes = Dish.query.filter(Dish.name.ilike(f'%{query}%')).all()  # Assuming 'Dish' is your model
        for dish in dishes:
            results.append({
                "id": dish.id,
                "name": dish.name,
                "price": dish.price,
            })

    return jsonify({"results": results})


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        contact_number = request.form['contact_number']

        # Validate duplicate username or email
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            if existing_user.username == username:
                flash('Username already exists!', 'danger')
            if existing_user.email == email:
                flash('Email already exists!', 'danger')
            return redirect(url_for('register'))

        # Hash password and create new user
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password, contact_number=contact_number)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/register_retailer', methods=['GET', 'POST'])
def register_retailer():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        contact_number = request.form['contact_number']
        address = request.form['address']
        city = request.form['city']

        # Check passwords
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register_retailer'))

        # Check email uniqueness
        if Retailer.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('register_retailer'))

        # Hash password and create retailer
        hashed_password = generate_password_hash(password)
        new_retailer = Retailer(name=name, email=email, password=hashed_password,
                                contact_number=contact_number, address=address, city=city)
        db.session.add(new_retailer)
        db.session.commit()

        flash('Retailer registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register_retailer.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session.clear()

        username = request.form['username']
        password = request.form['password']

        # Check for regular user
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
            session['is_user'] = not user.is_admin
            session['is_retailer'] = False

            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('dashboard'))

        # Check for retailer
        retailer = Retailer.query.filter_by(name=username).first()
        if retailer and check_password_hash(retailer.password, password):
            session['user_id'] = retailer.id
            session['is_admin'] = False
            session['is_user'] = False
            session['is_retailer'] = True
            return redirect(url_for('retailer_dashboard'))

        flash('Invalid credentials. Please try again.', 'danger')
    return render_template('login.html')



@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        flash('You need to log in to access this page.', 'danger')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        contact_number = request.form.get('contact_number')

        # Check email uniqueness
        if email and User.query.filter(User.email == email, User.id != user.id).first():
            flash('Email is already in use.', 'danger')
            return render_template('edit_profile.html', user=user)

        # Update user details
        if username:
            user.username = username
        if email:
            user.email = email
        if contact_number:
            user.contact_number = contact_number

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('edit_profile.html', user=user)


@app.route('/forget', methods=['GET', 'POST'])
def forget():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            session['reset_user_id'] = user.id
            flash('Please reset your password.', 'success')
            return redirect(url_for('reset_password'))
        flash('No account found with that email.', 'danger')
    return render_template('forget_password.html')


@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_user_id' not in session:
        flash('Unauthorized access. Please try again.', 'danger')
        return redirect(url_for('forget'))

    if request.method == 'POST':
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        user = User.query.get(session['reset_user_id'])
        if user:
            user.password = hashed_password
            db.session.commit()
            session.pop('reset_user_id', None)
            flash('Password has been reset successfully!', 'success')
            return redirect(url_for('login'))

    return render_template('reset_password.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    return render_template('dashboard.html', user=user)

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    users = User.query.all()
    retailers = Retailer.query.all()
    return render_template('admin_dashboard.html',users=users,retailers=retailers)

@app.route('/retailer_dashboard')
def retailer_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    retailer = Retailer.query.get(session['user_id'])
    if not retailer:
        flash('Retailer not found.', 'danger')
        return redirect(url_for('home'))

    # Fetch the retailer's restaurants
    restaurants = Restaurant.query.filter_by(retailer_id=retailer.id).all()
    dishes = Dish.query.filter_by(retailer_id=retailer.id).all()

    return render_template('retailer_dashboard.html', retailer=retailer, restaurants=restaurants, dishes=dishes)



@app.route('/edit_retailer_profile', methods=['GET', 'POST'])
def edit_retailer_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    retailer = Retailer.query.get(session['user_id'])
    if request.method == 'POST':
        retailer.name = request.form['name']
        retailer.contact_number = request.form['contact_number']
        retailer.address = request.form['address']
        retailer.city = request.form['city']
        db.session.commit()

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('retailer_dashboard'))

    return render_template('edit_retailer_profile.html', retailer=retailer)


@app.route('/city')
def city():
    location_id = request.args.get('location_id')

    if location_id:
        location = Location.query.get(location_id)
        if location:
            restaurants = Restaurant.query.filter_by(location_id=location_id).all()
            return render_template('city_dish.html', restaurants=restaurants, location_name=location.city_name)
        else:
            flash('Location not found.', 'danger')
            return redirect(url_for('home'))
    else:
        flash('No location specified.', 'danger')
        return redirect(url_for('home'))


@app.route('/addlocation', methods=['GET', 'POST'])
def add_location():
    # Check if the user is logged in and is an admin
    if 'is_admin' in session and session['is_admin']:
        if request.method == 'POST':
            # Get the city name from the form
            city_name = request.form.get('city_name')
            
            # Validate the input
            if not city_name:
                flash('City name is required!', 'danger')
                return redirect(url_for('add_location'))
            
            # Add the location to the database
            new_location = Location(city_name=city_name)
            db.session.add(new_location)
            db.session.commit()
            flash('Location added successfully!', 'success')
            return redirect(url_for('add_location'))
        
        # Render the form if GET request
        return render_template('add_location.html')
    else:
        # Redirect to the login page if not an admin
        flash('You must be an admin to access this page!', 'danger')
        return redirect(url_for('login'))


@app.route('/adddish', methods=['GET', 'POST'])
def add_dish():
    # Check if the user is logged in and is a retailer
    if 'user_id' not in session or not session.get('is_retailer'):
        flash('You must be logged in as a retailer to add a dish.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Retrieve the form data
        dish_name = request.form['dish_name']
        description = request.form['description']
        price = request.form['price']
        restaurant_id = request.form['restaurant_id']
        category = request.form['category']

        # Handle image upload
        image_file = request.files.get('image_file')
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
            # Use url_for to generate the image URL
            image_url = url_for('static', filename=f'image/{filename}')
        else:
            image_url = url_for('static', filename='default.jpg')

        # Find the retailer's restaurant to associate the dish
        retailer = Retailer.query.get(session['user_id'])
        if not retailer:
            flash('You are not associated with any retailer.', 'danger')
            return redirect(url_for('retailer_dashboard'))

        restaurant = Restaurant.query.filter_by(id=restaurant_id, retailer_id=retailer.id).first()
        if not restaurant:
            flash('Restaurant not found or you do not have access to this restaurant.', 'danger')
            return redirect(url_for('retailer_dashboard'))

        # Create and add the new dish
        new_dish = Dish(
            dish_name=dish_name,
            description=description,
            image_url=image_url,
            price=price,
            restaurant_id=restaurant.id,
            retailer_id=retailer.id,
            category=category
        )
        db.session.add(new_dish)
        db.session.commit()

        flash(f'{dish_name} has been added successfully!', 'success')
        return redirect(url_for('retailer_dashboard'))

    # If GET request, render the form to add a dish
    restaurants = Restaurant.query.filter_by(retailer_id=session['user_id']).all()
    return render_template('add_dish.html', restaurants=restaurants)


@app.route('/edit_dish/<int:dish_id>', methods=['GET', 'POST'])
def edit_dish(dish_id):
    # Check if the user is logged in and is a retailer
    if 'user_id' not in session or not session.get('is_retailer'):
        flash('You must be logged in as a retailer to edit a dish.', 'danger')
        return redirect(url_for('login'))

    # Get the dish from the database
    dish = Dish.query.get_or_404(dish_id)

    # Check if the logged-in retailer is the owner of the dish
    if dish.retailer_id != session['user_id']:
        flash('You are not authorized to edit this dish.', 'danger')
        return redirect(url_for('retailer_dashboard'))

    if request.method == 'POST':
        # Get form data
        dish.dish_name = request.form['dish_name']
        dish.description = request.form['description']
        dish.price = request.form['price']

        # Handle image upload
        image_file = request.files.get('image_file')
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
            dish.image_url = f'static/image/{filename}'  # Update the image URL in the database

        # Commit the changes to the database
        db.session.commit()

        flash(f'Dish "{dish.dish_name}" updated successfully!', 'success')
        return redirect(url_for('retailer_dashboard'))  # Redirect to retailer dashboard or dish list

    # Render the form to edit the dish
    return render_template('edit_dish.html', dish=dish)


@app.route('/delete_dish/<int:dish_id>', methods=['GET'])
def delete_dish(dish_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    dish = Dish.query.get(dish_id)
    if not dish:
        flash('Dish not found.', 'danger')
        return redirect(url_for('retailer_dashboard'))

    # Ensure the dish belongs to the logged-in retailer
    if dish.retailer_id != session['user_id']:
        flash('You do not have permission to delete this dish.', 'danger')
        return redirect(url_for('retailer_dashboard'))

    db.session.delete(dish)
    db.session.commit()

    flash('Dish deleted successfully!', 'success')
    return redirect(url_for('retailer_dashboard'))


# This is for retailer only
@app.route('/all_dishes')
def all_dishes():
    if 'user_id' not in session or not session.get('is_retailer'):
        flash('You must be logged in as a retailer to view this page.', 'danger')
        return redirect(url_for('login'))
    retailer_id = session.get('user_id')

    dishes = Dish.query.filter_by(retailer_id=retailer_id).all()
    return render_template('all_dishes.html',dishes=dishes)


@app.route('/restaurant/<int:restaurant_id>', methods=['GET'])
def view_dishes(restaurant_id):
    # Get the restaurant by ID
    restaurant = Restaurant.query.get_or_404(restaurant_id)

    # Get all dishes for this restaurant
    dishes = Dish.query.filter_by(restaurant_id=restaurant_id).all()

    return render_template('view_dishes.html', restaurant=restaurant, dishes=dishes)


@app.route('/item_list/<category_name>')
def item_list(category_name):
    # Fetch all items in the selected category from the database
    items = Dish.query.filter(Dish.category == category_name).all()

    return render_template('item_list.html', items=items, category_name=category_name)


@app.route('/add_restaurant', methods=['GET', 'POST'])
def add_restaurant():
    # Check if the user is logged in and is a retailer
    if 'user_id' not in session or not session.get('is_retailer'):
        flash('You must be logged in as a retailer to add a restaurant.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Get form data
        restaurant_name = request.form['restaurant_name']
        cuisine = request.form['cuisine']
        distance = request.form['distance']
        rating = request.form['rating']

        image_file = request.files.get('image_file')  # Get the uploaded file
        if image_file and allowed_file(image_file.filename):  # Check validity
            filename = secure_filename(image_file.filename)  # Secure the filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)  # Full path
            image_file.save(file_path)  # Save the file to the folder
            image_url = f'static/image/{filename}'  # Generate the URL
        else:
            image_url = 'static/default.jpg'  # Use a default image if no file uploaded

        # Get the retailer (associated with the logged-in user)
        retailer = Retailer.query.get(session['user_id'])
        if not retailer:
            flash('Retailer not found.', 'danger')
            return redirect(url_for('home'))

        city = retailer.city

        # Get the location associated with the retailer's city
        location = Location.query.filter_by(city_name=city).first()

        if not location:
            flash(f'Location for city "{city}" not found.', 'danger')
            return redirect(url_for('home'))

        location_id = location.id  # Retrieve the location ID

        # Create a new restaurant and associate it with the retailer and location
        new_restaurant = Restaurant(
            restaurant_name=restaurant_name,
            location_id=location_id,
            cuisine=cuisine,
            distance=distance,
            rating=rating,
            image_url=image_url,
            retailer_id=retailer.id  # Associate the restaurant with the retailer
        )

        # Add the restaurant to the session and commit
        db.session.add(new_restaurant)
        db.session.commit()

        flash(f'Your restaurant "{restaurant_name}" has been added successfully!', 'success')
        return redirect(url_for('retailer_dashboard'))  # Redirect to retailer's dashboard

    return render_template('add_restaurant.html')  # Render the form if it's a GET request


@app.route('/edit_restaurant/<int:restaurant_id>', methods=['GET', 'POST'])
def edit_restaurant(restaurant_id):
    # Check if the user is logged in and is a retailer
    if 'user_id' not in session or not session.get('is_retailer'):
        flash('You must be logged in as a retailer to edit a restaurant.', 'danger')
        return redirect(url_for('login'))

    # Get the restaurant to edit
    restaurant = Restaurant.query.get_or_404(restaurant_id)

    # Check if the restaurant belongs to the logged-in retailer
    if restaurant.retailer_id != session['user_id']:
        flash('You cannot edit this restaurant.', 'danger')
        return redirect(url_for('restaurants_list'))

    if request.method == 'POST':
        # Update restaurant details
        restaurant.restaurant_name = request.form['restaurant_name']
        restaurant.cuisine = request.form['cuisine']
        restaurant.distance = request.form['distance']
        restaurant.rating = request.form['rating']

        # Handle image upload
        image_file = request.files.get('image_file')
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
            restaurant.image_url = f'static/image/{filename}'  # Update the image URL in the database

        # Commit changes to the database
        db.session.commit()

        flash(f'Restaurant "{restaurant.restaurant_name}" has been updated successfully!', 'success')
        return redirect(url_for('retailer_dashboard'))

    # Render the edit restaurant form
    return render_template('edit_restaurant.html', restaurant=restaurant)


@app.route('/delete_restaurant/<int:restaurant_id>', methods=['POST'])
def delete_restaurant(restaurant_id):
    # Check if the user is logged in and is a retailer
    if 'user_id' not in session or not session.get('is_retailer'):
        flash('You must be logged in as a retailer to delete a restaurant.', 'danger')
        return redirect(url_for('login'))

    # Get the restaurant to delete
    restaurant = Restaurant.query.get_or_404(restaurant_id)

    # Check if the restaurant belongs to the logged-in retailer
    if restaurant.retailer_id != session['user_id']:
        flash('You cannot delete this restaurant.', 'danger')
        return redirect(url_for('restaurants_list'))

    # Delete the restaurant
    db.session.delete(restaurant)
    db.session.commit()

    flash(f'Restaurant "{restaurant.restaurant_name}" has been deleted successfully.', 'success')
    return redirect(url_for('restaurants_list'))

@app.route('/browse_restaurants', methods=['GET'])
def browse_restaurants():
    # Fetch all restaurants and their dishes
    restaurants = Restaurant.query.options(db.joinedload(Restaurant.dishes)).all()

    return render_template('browse_restaurants.html', restaurants=restaurants)

# this for retailer only retailer can see this
@app.route('/all_restaurants')
def all_restaurants():
    # Check if the user is logged in and is a retailer
    if 'user_id' not in session or not session.get('is_retailer'):
        flash('You must be logged in as a retailer to view this page.', 'danger')
        return redirect(url_for('login'))

    # Get the retailer's ID from the session
    retailer_id = session.get('user_id')

    # Fetch restaurants associated with the retailer
    # Update this query as per your database schema
    restaurants = Restaurant.query.filter_by(retailer_id=retailer_id).all()

    return render_template('all_restaurants.html', restaurants=restaurants)

@app.route('/order')
def order():
    # Ensure the user is logged in
    if 'user_id' not in session:
        flash('Please log in to view your orders.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Fetch pending orders
    current_orders = Order.query.filter_by(user_id=user_id, status='Pending').all()

    # Update pending orders to "Delivered" if delivery time has passed
    now = datetime.now()
    for order in current_orders:
        if now >= order.delivery_time:
            order.status = 'Delivered'
    db.session.commit()

    # Fetch the updated current orders and order history
    current_orders = Order.query.filter_by(user_id=user_id, status='Pending').all()
    order_history = Order.query.filter(Order.user_id == user_id, Order.status != 'Pending').all()

    return render_template(
        'orders.html',
        current_orders=current_orders,
        order_history=order_history,
        datetime=datetime
    )



@app.route('/place_order', methods=['POST'])
def place_order():
    if 'user_id' not in session:
        flash('Please log in to place an order.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    cart_items = Cart.query.filter_by(user_id=user_id).all()

    if not cart_items:
        flash('Your cart is empty. Add items before placing an order.', 'danger')
        return redirect(url_for('cart'))

    # Create a new order with delivery time set to 25 minutes from now
    order = Order(
        user_id=user_id,
        delivery_time=datetime.now() + timedelta(minutes=25)
    )
    db.session.add(order)
    db.session.flush()  # Ensure the order ID is available

    # Add items from the cart to the order
    for item in cart_items:
        order_item = OrderItem(order_id=order.id, dish_id=item.dish_id, quantity=item.quantity)
        db.session.add(order_item)
        db.session.delete(item)  # Remove item from the cart

    db.session.commit()

    flash('Your order has been placed successfully!', 'success')
    return redirect(url_for('order'))

@app.route('/view_orders')
def view_orders():
    if 'user_id' not in session:
        flash('You need to log in to view your orders.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Fetch current and historical orders
    current_orders = Order.query.filter_by(user_id=user_id, status='Pending').all()
    order_history = Order.query.filter(Order.user_id == user_id, Order.status != 'Pending').all()

    return render_template(
        'orders.html',
        current_orders=current_orders,
        order_history=order_history,
        datetime=datetime
    )



@app.route('/cart', methods=['GET'])
def cart():
    # Ensure the user is logged in
    if 'user_id' not in session:
        flash('Please log in to view your cart.', 'danger')
        return redirect(url_for('login'))

    # Get the user's cart items
    cart_items = Cart.query.filter_by(user_id=session['user_id']).all()

    return render_template('Cart.html', cart_items=cart_items)


@app.route('/add_to_cart/<int:dish_id>', methods=['POST'])
def add_to_cart(dish_id):
    # Ensure the user is logged in
    if 'user_id' not in session:
        flash('Please log in to add items to your cart.', 'danger')
        return redirect(url_for('login'))

    # Check if the dish exists
    dish = Dish.query.get_or_404(dish_id)

    # Check if the dish is already in the user's cart
    cart_item = Cart.query.filter_by(user_id=session['user_id'], dish_id=dish_id).first()
    if cart_item:
        # Increase the quantity if it exists
        cart_item.quantity += 1
    else:
        # Otherwise, create a new cart item
        cart_item = Cart(user_id=session['user_id'], dish_id=dish_id, quantity=1)
        db.session.add(cart_item)

    db.session.commit()

    flash(f'"{dish.dish_name}" has been added to your cart.', 'success')
    return redirect(url_for('view_dishes', restaurant_id=dish.restaurant_id))



@app.route('/remove_from_cart/<int:cart_id>', methods=['POST'])
def remove_from_cart(cart_id):
    # Ensure the user is logged in
    if 'user_id' not in session:
        flash('Please log in to modify your cart.', 'danger')
        return redirect(url_for('login'))

    # Find the cart item
    cart_item = Cart.query.get_or_404(cart_id)

    # Check if the cart item belongs to the logged-in user
    if cart_item.user_id != session['user_id']:
        flash('You cannot remove items from another user\'s cart.', 'danger')
        return redirect(url_for('view_cart'))

    # Remove the item from the cart
    db.session.delete(cart_item)
    db.session.commit()

    flash(f'"{cart_item.dish.dish_name}" has been removed from your cart.', 'success')
    return redirect(url_for('view_cart'))

@app.route('/maintanance',methods=['GET','POST'])
def maintanance():
    return render_template('maintanance.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('is_admin', None)
    flash('Logged out successfully.', 'success')
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
