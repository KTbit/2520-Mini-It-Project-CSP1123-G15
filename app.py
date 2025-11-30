<<<<<<< HEAD
import json

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from databasemodels import db, User, SavedRecipe, ShoppingList
from config import Config
from utilities import search_recipes_by_ingredients, get_recipe_details


# -------------------------------------------------
# Application factory
# -------------------------------------------------
app = Flask(__name__)
app.config.from_object(Config)

# Initialise extensions
=======
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from databasemodels import db, User, SavedRecipe #shopping list db to be made by Salman
from config import Config
from utilities import search_recipes_by_ingredients, get_recipe_details #shopping list...nutrition / scaling calculator wip

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
>>>>>>> 65b9ef74ff36e65d62039d53d2ac1714437d849f
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
<<<<<<< HEAD
login_manager.login_view = "user_login"  # redirect here when login is required


@login_manager.user_loader
def load_user(user_id: str):
    """Callback for Flask‑Login to load a user from the DB."""
    try:
        return User.query.get(int(user_id))
    except (TypeError, ValueError):
        return None


# Create DB tables if they do not exist
with app.app_context():
    db.create_all()


# -------------------------------------------------
# Routes: Public
# -------------------------------------------------
@app.route("/")
def index():
    """Homepage with search form."""
    return render_template("index.html")


@app.route("/recipes/browse")
def recipe_browse():
    """Browse/search recipes by ingredients.

    Expects a query parameter 'ingredients' in the URL, e.g.:

        /recipes/browse?ingredients=egg,tomato,cheese
    """
    ingredients = request.args.get("ingredients", "", type=str).strip()
    recipes = []

    if ingredients:
        recipes = search_recipes_by_ingredients(ingredients, number=12)

    return render_template(
        "recipe_section/recipebrowse.html",
        ingredients=ingredients,
        recipes=recipes,
    )


@app.route("/recipes/<int:recipe_id>")
def recipe_detail(recipe_id: int):
    """Show full details for a single recipe."""
    details = get_recipe_details(recipe_id)
    if details is None:
        flash("Could not load recipe details. Please try again later.", "danger")
        return redirect(url_for("index"))

    # Check if this recipe is already saved by the current user
    is_saved = False
    if current_user.is_authenticated:
        is_saved = (
            SavedRecipe.query.filter_by(
                user_id=current_user.id, recipe_id=recipe_id
            ).first()
            is not None
        )

    return render_template(
        "recipe_section/recipedetail.html",
        recipe=details,
        is_saved=is_saved,
    )


# -------------------------------------------------
# Routes: Authentication (User)
# -------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def user_register():
    if current_user.is_authenticated:
        return redirect(url_for("user_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("user_register"))

        # Check uniqueness
        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for("user_register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return redirect(url_for("user_register"))

        # Create user
        new_user = User(username=username, email=email)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("user_login"))

    return render_template("user/user_register.html")


@app.route("/login", methods=["GET", "POST"])
def user_login():
    if current_user.is_authenticated:
        return redirect(url_for("user_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash("Invalid username or password.", "danger")
            return redirect(url_for("user_login"))

        login_user(user)
        flash("Logged in successfully.", "success")
        return redirect(url_for("user_dashboard"))

    return render_template("user/user_login.html")


@app.route("/logout")
@login_required
def user_logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def user_dashboard():
    """Simple user dashboard showing saved recipes."""
    saved = SavedRecipe.query.filter_by(user_id=current_user.id).all()
    return render_template("user/userdashboard.html", saved_recipes=saved)


@app.route("/recipes/<int:recipe_id>/save", methods=["POST"])
@login_required
def save_recipe(recipe_id: int):
    """Save a recipe to the current user's favourites."""
    recipe_name = request.form.get("recipe_name", "").strip() or "Recipe"

    existing = SavedRecipe.query.filter_by(
        user_id=current_user.id, recipe_id=recipe_id
    ).first()
    if existing:
        flash("Recipe already in your saved list.", "info")
        return redirect(url_for("recipe_detail", recipe_id=recipe_id))

    saved = SavedRecipe(
        user_id=current_user.id,
        recipe_id=recipe_id,
        recipe_name=recipe_name,
    )
    db.session.add(saved)
    db.session.commit()

    flash("Recipe saved to your favourites.", "success")
    return redirect(url_for("recipe_detail", recipe_id=recipe_id))


@app.route("/recipes/<int:recipe_id>/unsave", methods=["POST"])
@login_required
def unsave_recipe(recipe_id: int):
    """Remove a saved recipe from the current user's favourites."""
    saved = SavedRecipe.query.filter_by(
        user_id=current_user.id, recipe_id=recipe_id
    ).first()
    if not saved:
        flash("Recipe was not in your saved list.", "info")
        return redirect(url_for("recipe_detail", recipe_id=recipe_id))

    db.session.delete(saved)
    db.session.commit()
    flash("Recipe removed from your favourites.", "success")
    return redirect(url_for("recipe_detail", recipe_id=recipe_id))



# -------------------------------------------------
# Routes: Shopping List (Week 4 feature)
# -------------------------------------------------
@app.route("/shopping-list")
@login_required
def shopping_list():
    """Display the current user's shopping list."""
    items = ShoppingList.query.filter_by(user_id=current_user.id).order_by(
        ShoppingList.created_at.desc()
    ).all()
    return render_template("user/shopping_list.html", items=items)


@app.route("/recipes/<int:recipe_id>/add-to-shopping-list", methods=["POST"])
@login_required
def add_to_shopping_list(recipe_id: int):
    """Add a recipe's ingredients to the current user's shopping list.

    For simplicity, we fetch the recipe details again from Spoonacular here and
    store the ingredient strings as JSON.
    """
    # Check if already in shopping list
    existing = ShoppingList.query.filter_by(
        user_id=current_user.id, recipe_id=recipe_id
    ).first()
    if existing:
        flash("This recipe is already in your shopping list.", "info")
        return redirect(url_for("recipe_detail", recipe_id=recipe_id))

    details = get_recipe_details(recipe_id)
    if details is None:
        flash("Could not fetch recipe details to build shopping list.", "danger")
        return redirect(url_for("recipe_detail", recipe_id=recipe_id))

    ingredients_list = []
    for ing in details.get("extendedIngredients", []):
        text = ing.get("original") or ing.get("name")
        if text:
            ingredients_list.append(text)

    if not ingredients_list:
        flash("No ingredients found for this recipe.", "warning")
        return redirect(url_for("recipe_detail", recipe_id=recipe_id))

    entry = ShoppingList(
        user_id=current_user.id,
        recipe_id=recipe_id,
        recipe_name=details.get("title", "Recipe"),
        ingredients_json=json.dumps(ingredients_list),
    )
    db.session.add(entry)
    db.session.commit()

    flash("Recipe added to your shopping list.", "success")
    return redirect(url_for("shopping_list"))


@app.route("/shopping-list/<int:item_id>/remove", methods=["POST"])
@login_required
def remove_from_shopping_list(item_id: int):
    """Remove an entry from the current user's shopping list."""
    item = ShoppingList.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        flash("You cannot modify another user's shopping list.", "danger")
        return redirect(url_for("shopping_list"))

    db.session.delete(item)
    db.session.commit()
    flash("Item removed from your shopping list.", "success")
    return redirect(url_for("shopping_list"))


# -------------------------------------------------
# Routes: Admin
# -------------------------------------------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username, is_admin=True).first()
        if user is None or not user.check_password(password):
            flash("Invalid admin credentials.", "danger")
            return redirect(url_for("admin_login"))

        login_user(user)
        flash("Admin login successful.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin/admin_login.html")


@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash("Access denied. Admin only.", "danger")
        return redirect(url_for("index"))

    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/admin_dashboard.html", users=users)


# -------------------------------------------------
# Entry point
# -------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
=======
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
def  user_register():
    if current_user.is_authenticated:
        return redirect(url_for('user_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # check if username exists...
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('user_register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('user_register'))
    
        # for registering new users into the system
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('user_login'))
    
    return render_template('user/user_register.html')

@app.route('/login', methods=['GET', 'POST'])
def user_login(): 
    if current_user.is_authenticated:
        return redirect(url_for('user_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('user_dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('user/user_login.html')

@app.route('/logout')
@login_required
def user_logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# User dashboard route

@app.route('/dashboard')
@login_required
def user_dashboard():
    saved_recipes = SavedRecipe.query.filter_by(user_id=current_user.id).all()
    return render_template('user/userdashboard.html', saved_recipes=saved_recipes)

# Recipes route

@app.route('/recipes/browse')
def recipe_browse():
    # to add recipe browsing logic
    return render_template('recipe_section/recipebrowse.html')

@app.route('/recipes/<int:recipe_id>')
def recipe_detail(recipe_id):
    # to add recipe detail logic
    return render_template('recipe_section/recipedetail.html', recipe_id=recipe_id)

#admin routes

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

#admin route(s) WIP - maybe admins can register / add new admins under their supervision(?)

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied. Admin only.', 'danger')
        return redirect(url_for('index'))
    
    users = User.query.all()
    return render_template('admin/admin_registration.html', users=users)

# for admin registration

@app.route('/admin/register', methods=['GET', 'POST'])
@login_required
def admin_register():
    if not current_user.is_admin:
        flash('Access denied. Admin only.', 'danger')
        return redirect(url_for('index'))
    
    return render_template('admin/admin_registration.html')

# run the app

if __name__ == '__main__':
    app.run(debug=True)


>>>>>>> 65b9ef74ff36e65d62039d53d2ac1714437d849f
