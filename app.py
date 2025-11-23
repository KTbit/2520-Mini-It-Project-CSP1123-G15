from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from databasemodels import db, User, SavedRecipe #shopping list db to be made by Salman
from config import Config
from utilities import search_recipes_by_ingredients, get_recipe_details #shopping list...nutrition / scaling calculator wip

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# creating the database tables
with app.app_context():
    db.create_all()

# Public route(s)

@app.route('/')
def index():
    return render_template('index.html')

# User authentication (logging in/out, registering) routes

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Validation
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
        
        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('user/user_register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('user/user_login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# ============= USER ROUTES =============

@app.route('/dashboard')
@login_required
def dashboard():
    saved_recipes = SavedRecipe.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', saved_recipes=saved_recipes)

# ============= RECIPE ROUTES =============

@app.route('/recipes/search', methods=['GET', 'POST'])
def search_recipes():
    if request.method == 'POST':
        ingredients = request.form.get('ingredients')
        recipes = search_recipes_by_ingredients(ingredients)
        return render_template('recipe_section/recipebrowse.html', recipes=recipes, query=ingredients)
    
    return render_template('recipe_section/recipebrowse.html', recipes=None)

@app.route('/recipes/<int:recipe_id>')
def recipe_detail(recipe_id):
    recipe = get_recipe_details(recipe_id)
    if not recipe:
        flash('Recipe not found', 'danger')
        return redirect(url_for('search_recipes'))
    
    return render_template('recipe_section/recipedetail.html', recipe=recipe)

@app.route('/recipes/<int:recipe_id>/save', methods=['POST'])
@login_required
def save_recipe(recipe_id):
    # see if the recipe has already been saved by the user
    existing = SavedRecipe.query.filter_by(user_id=current_user.id, recipe_id=recipe_id).first()
    if existing:
        flash('Recipe already saved', 'info')
        return redirect(url_for('recipe_detail', recipe_id=recipe_id))
    
    # Get recipe name from API
    recipe = get_recipe_details(recipe_id)
    if not recipe:
        flash('Could not save recipe', 'danger')
        return redirect(url_for('search_recipes'))
    
    saved_recipe = SavedRecipe(
        user_id=current_user.id,
        recipe_id=recipe_id,
        recipe_name=recipe['title']
    )
    
    db.session.add(saved_recipe)
    db.session.commit()
    
    flash('Recipe saved!', 'success')
    return redirect(url_for('recipe_detail', recipe_id=recipe_id))

# ============= ADMIN ROUTES =============

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_admin:
            login_user(user)
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials', 'danger')
    
    return render_template('admin/admin_login.html')

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    users = User.query.all()
    return render_template('admin/admin_dashboard.html', users=users)

# ============= RUN APP =============

if __name__ == '__main__':
    app.run(debug=True)