import json

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    make_response
)
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

from functools import wraps
from databasemodels import db, User, SavedRecipe, ShoppingList, Post, Comment, Collection
from config import Config
from utilities import search_recipes_by_ingredients, get_recipe_details, get_recipe_cached, autocomplete_ingredients




app = Flask(__name__)
app.config.from_object(Config)

# Initialise extensions
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
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



@app.route("/")
def index():
    #get recent posts
    recent_posts = Post.query.order_by(Post.created_at.desc()).limit(6).all()

    #trying to debug
    print(f"[DEBUG] Passing {len(recent_posts)} posts to homepage")

    return render_template("index.html", recent_posts = recent_posts)

#WEEK 5 - added category filtering based on price and time taken - lowest to highest, vice versa (modified recipebrowse route)

# WEEK 7 EDIT : further optimized the code to present clearer recipe search categroy filters. new variable : cuisine

@app.route("/recipes/browse")
def recipe_browse():
    """Enhanced recipe browsing with category filters."""
    ingredients = request.args.get("ingredients", "", type=str).strip()
    
    # Get filter parameters
    cuisine = request.args.get("cuisine", "", type=str).strip()
    diet = request.args.get("diet", "", type=str).strip()
    meal_type = request.args.get("type", "", type=str).strip()
    max_time = request.args.get("maxReadyTime", "", type=str).strip()
    
    recipes = []
    
    # Build filters dictionary
    filters = {}
    if cuisine:
        filters['cuisine'] = cuisine
    if diet:
        filters['diet'] = diet
    if meal_type:
        filters['type'] = meal_type
    if max_time:
        try:
            filters['maxReadyTime'] = int(max_time)
        except ValueError:
            pass
    
    # Search with ingredients and/or filters
    if ingredients or filters:
        recipes = search_recipes_by_ingredients(
            ingredients if ingredients else "",
            number=12,
            **filters
        )
    
    # Prepare active filters for display
    active_filters = {
        'ingredients': ingredients,
        'cuisine': cuisine,
        'diet': diet,
        'type': meal_type,
        'maxReadyTime': max_time,
    }
    
    return render_template(
        "recipe_section/recipebrowse.html",
        recipes=recipes,
        active_filters=active_filters,
    )

# week 9 - added the route for autocompleting ingredients in search. its like recipe radar, super cook websites, etc
@app.route("/api/autocomplete/ingredients")
def api_autocomplete_ingredients():
    """API endpoint for ingredient autocomplete suggestions."""
    query = request.args.get("q", "").strip()
    
    if not query or len(query) < 2:
        return {"suggestions": []}
    
    suggestions = autocomplete_ingredients(query, number=8)
    return {"suggestions": suggestions}
            

@app.route("/recipes/<int:recipe_id>")
def recipe_detail(recipe_id: int):
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

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for("user_register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return redirect(url_for("user_register"))

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

# User post creation / deletion feature - week 5 update

@app.route('/posts/create', methods=['POST'])
@login_required
def create_post():
    recipe_id = request.form.get('recipe_id')  # <-- if not working..change to spoonacular_id
    
    if not recipe_id:
        flash("No recipe specified!", "danger")
        return redirect(url_for('index'))
    
    # Fetch recipe info
    recipe = get_recipe_cached(int(recipe_id))
    
    if not recipe:
        flash("Could not fetch recipe details!", "danger")
        return redirect(url_for('index'))
    
    # Check if user already posted this recipe
    existing = Post.query.filter_by(
        user_id=current_user.id, 
        spoonacular_id=int(recipe_id)
    ).first()
    
    if existing:
        flash("You've already shared this recipe!", "info")
        return redirect(url_for('post_view', post_id=existing.id))
    
    # Create post
    post = Post(
        user_id=current_user.id, 
        spoonacular_id=int(recipe_id),
        title=recipe.get('title', 'Untitled Recipe'), 
        image=recipe.get('image')
    )
    
    db.session.add(post)
    db.session.commit()
    
    flash("Recipe shared successfully! 🎉", "success")
    return redirect(url_for('post_view', post_id=post.id))


@app.route('/posts/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    p = Post.query.get_or_404(post_id)
    if p.author != current_user and not current_user.is_admin:
        abort(403)
    db.session.delete(p); db.session.commit()
    return redirect(url_for('index'))

@app.route('/posts')
def posts_feed():
    """Show all posts from users you follow (or all posts for now)"""
    if current_user.is_authenticated:
        # Show posts from followed users
        posts = Post.query.filter(
            Post.user_id.in_([u.id for u in current_user.followed.all()])
        ).order_by(Post.created_at.desc()).all()
    else:
        # Show all public posts
        posts = Post.query.order_by(Post.created_at.desc()).limit(20).all()
    
    return render_template('posts_feed.html', posts=posts)

# Week 8 - refurbished the post_view route and its html page
@app.route('/posts/<int:post_id>')
def post_view(post_id):
    """View a single post"""
    post = Post.query.get_or_404(post_id)
    recipe = get_recipe_cached(post.spoonacular_id)

    return render_template('post_view.html', post=post, recipe=recipe, Comment=Comment)


@app.route('/profile/<int:user_id>')
def profile(user_id):
    """View a user's profile"""
    user = User.query.get_or_404(user_id)
    posts = Post.query.filter_by(user_id=user_id).order_by(Post.created_at.desc()).all()
    
    is_following = False
    if current_user.is_authenticated:
        is_following = current_user.followed.filter_by(id=user_id).first() is not None
    
    return render_template('user/profile.html', user=user, posts=posts, is_following=is_following)

@app.route('/follow/<int:user_id>', methods=['POST'])
@login_required
def follow(user_id):
    user_to_follow = User.query.get_or_404(user_id)
    if user_to_follow == current_user:
        flash("Can't follow yourself", 'warning')
        return redirect(url_for('profile', user_id=user_id))
    if not current_user.followed.filter_by(id=user_to_follow.id).first():
        current_user.followed.append(user_to_follow)
        db.session.commit()
    return redirect(url_for('profile', user_id=user_id))

@app.route('/unfollow/<int:user_id>', methods=['POST'])
@login_required
def unfollow(user_id):
    user = User.query.get_or_404(user_id)
    if current_user.followed.filter_by(id=user.id).first():
        current_user.followed.remove(user)
        db.session.commit()
    return redirect(url_for('profile', user_id=user_id))

# Week 10 - refurbished comments; route and appearance-wise

from databasemodels import db, User, SavedRecipe, ShoppingList, Post, Comment

@app.route('/posts/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    """Add a comment to a post"""
    post = Post.query.get_or_404(post_id)
    comment_text = request.form.get('comment', '').strip()
    
    if not comment_text:
        flash("Comment cannot be empty!", "warning")
        return redirect(url_for('post_view', post_id=post_id))
    
    if len(comment_text) > 500:
        flash("Comment is too long! Maximum 500 characters.", "warning")
        return redirect(url_for('post_view', post_id=post_id))
    
    comment = Comment(
        user_id=current_user.id,
        post_id=post_id,
        body=comment_text
    )
    
    db.session.add(comment)
    db.session.commit()
    
    flash("Comment added! 💬", "success")
    return redirect(url_for('post_view', post_id=post_id))


@app.route('/posts/<int:post_id>/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(post_id, comment_id):
    """Delete a comment (only by author or admin)"""
    comment = Comment.query.get_or_404(comment_id)
    
    # Check if user is author or admin
    if comment.user_id != current_user.id and not current_user.is_admin:
        flash("You can only delete your own comments!", "danger")
        return redirect(url_for('post_view', post_id=post_id))
    
    db.session.delete(comment)
    db.session.commit()
    
    flash("Comment deleted.", "info")
    return redirect(url_for('post_view', post_id=post_id))



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

@app.route("/shopping-list/pdf")
@login_required
def shopping_list_pdf():
    """Generate and download shopping list as PDF"""
    
    items = ShoppingList.query.filter_by(user_id=current_user.id).order_by(
        ShoppingList.created_at.desc()
    ).all()
    
    if not items:
        flash('Your shopping list is empty!', 'info')
        return redirect(url_for('shopping_list'))
    
    # Create PDF in memory
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch)
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    
    # Add title
    title = Paragraph(f"Shopping List - {current_user.username}", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.3 * inch))
    
    # Process each recipe in the shopping list
    for item in items:
        # Recipe name as a heading
        recipe_heading = Paragraph(
            f"<b>{item.recipe_name}</b> (Recipe #{item.recipe_id})",
            styles['Heading2']
        )
        elements.append(recipe_heading)
        elements.append(Spacer(1, 0.1 * inch))
        
        # Get ingredients
        ingredients = item.ingredients()
        
        if ingredients:
            # Create table data
            data = [['☐', 'Ingredient']]  # Header
            for ing in ingredients:
                data.append(['☐', ing])
            
            # Create table
            table = Table(data, colWidths=[0.4*inch, 5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 0.3 * inch))
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF data
    pdf_data = buffer.getvalue()
    buffer.close()
    
    # Create response
    response = make_response(pdf_data)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=shopping_list_{current_user.username}.pdf'
    
    return response



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


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return wrapper



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
@admin_required
def admin_dashboard():
    if not current_user.is_admin:
        flash("Access denied. Admin only.", "danger")
        return redirect(url_for("index"))

    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/admin_dashboard.html", users=users)

#week 5 - added admin delete user route
@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def admin_delete_user(user_id: int):
    """Delete a user (admin only)"""
    user = User.query.get_or_404(user_id)
    
    if user.is_admin:
        flash("Cannot delete admin users.", "danger")
        return redirect(url_for('admin_dashboard'))
    
    db.session.delete(user)
    db.session.commit()
    flash(f"User '{user.username}' has been deleted.", "success")
    return redirect(url_for('admin_dashboard'))


from app import app, db
from databasemodels import Post 

with app.app_context():
    posts = Post.query.all()
    print(f"Total posts in database: {len(posts)}")
    for post in posts:
        print(f"-{post.title} by user {post.user_id}")


from app import app, db
from databasemodels import User

with app.app_context():
    admins = User.query.filter_by(is_admin=True).all()
    print(f"Found {len(admins)} admin(s):")
    for admin in admins:
        print(f"  - {admin.username} ({admin.email})")


# Week 9, 10 - newly added + modified Collection routes for the user dashboard overhaul

from databasemodels import db, User, SavedRecipe, ShoppingList, Post, Comment, Collection

# Helper function to ensure user has a default collection
def ensure_default_collection(user_id):
    """Create default 'My Recipes' collection if user doesn't have one."""
    default = Collection.query.filter_by(user_id=user_id, is_default=True).first()
    if not default:
        default = Collection(
            user_id=user_id,
            name="My Recipes",
            description="Your saved recipes",
            is_default=True
        )
        db.session.add(default)
        db.session.commit()
    return default


@app.route("/dashboard")
@login_required
def user_dashboard():
    """Pinterest-style dashboard showing recipe collections."""
    # Ensure user has default collection
    ensure_default_collection(current_user.id)
    
    collections = Collection.query.filter_by(user_id=current_user.id).order_by(
        Collection.is_default.desc(),  # Default collection first
        Collection.created_at.desc()
    ).all()
    
    return render_template("user/userdashboard.html", collections=collections)


@app.route("/collections/create", methods=["POST"])
@login_required
def create_collection():
    """Create a new recipe collection."""
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    
    if not name:
        flash("Collection name is required!", "danger")
        return redirect(url_for("user_dashboard"))
    
    if len(name) > 100:
        flash("Collection name is too long (max 100 characters).", "warning")
        return redirect(url_for("user_dashboard"))
    
    collection = Collection(
        user_id=current_user.id,
        name=name,
        description=description if description else None
    )
    
    db.session.add(collection)
    db.session.commit()
    
    flash(f"Collection '{name}' created! 📌", "success")
    return redirect(url_for("user_dashboard"))


@app.route("/collections/<int:collection_id>")
@login_required
def view_collection(collection_id):
    """View all recipes in a specific collection."""
    collection = Collection.query.get_or_404(collection_id)
    
    # Ensure user owns this collection
    if collection.user_id != current_user.id:
        flash("You don't have permission to view this collection.", "danger")
        return redirect(url_for("user_dashboard"))
    
    recipes = collection.recipes.order_by(SavedRecipe.saved_at.desc()).all()
    
    return render_template("user/collection_view.html", collection=collection, recipes=recipes)


@app.route("/collections/<int:collection_id>/edit", methods=["POST"])
@login_required
def edit_collection(collection_id):
    """Edit a collection's name and description."""
    collection = Collection.query.get_or_404(collection_id)
    
    if collection.user_id != current_user.id:
        flash("You cannot edit another user's collection.", "danger")
        return redirect(url_for("user_dashboard"))
    
    if collection.is_default:
        flash("Cannot edit the default collection.", "warning")
        return redirect(url_for("user_dashboard"))
    
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    
    if not name:
        flash("Collection name cannot be empty.", "danger")
        return redirect(url_for("user_dashboard"))
    
    collection.name = name
    collection.description = description if description else None
    db.session.commit()
    
    flash("Collection updated! ✏️", "success")
    return redirect(url_for("user_dashboard"))


@app.route("/collections/<int:collection_id>/delete", methods=["POST"])
@login_required
def delete_collection(collection_id):
    """Delete a collection (moves recipes to default collection)."""
    collection = Collection.query.get_or_404(collection_id)
    
    if collection.user_id != current_user.id:
        flash("You cannot delete another user's collection.", "danger")
        return redirect(url_for("user_dashboard"))
    
    if collection.is_default:
        flash("Cannot delete the default collection.", "warning")
        return redirect(url_for("user_dashboard"))
    
    # Move all recipes to default collection
    default_collection = ensure_default_collection(current_user.id)
    for recipe in collection.recipes.all():
        recipe.collection_id = default_collection.id
    
    db.session.delete(collection)
    db.session.commit()
    
    flash(f"Collection '{collection.name}' deleted. Recipes moved to 'My Recipes'.", "info")
    return redirect(url_for("user_dashboard"))


# MODIFY your existing save_recipe route to support collections:
@app.route("/recipes/<int:recipe_id>/save", methods=["POST"])
@login_required
def save_recipe(recipe_id: int):
    """Save recipe to a collection (with collection selection)."""
    recipe_name = request.form.get("recipe_name", "").strip() or "Recipe"
    recipe_image = request.form.get("recipe_image", "").strip()
    collection_id = request.form.get("collection_id")
    
    # Check if already saved
    existing = SavedRecipe.query.filter_by(
        user_id=current_user.id, recipe_id=recipe_id
    ).first()
    if existing:
        flash("Recipe already in your saved list.", "info")
        return redirect(url_for("recipe_detail", recipe_id=recipe_id))
    
    # If no collection specified, use default
    if not collection_id:
        default_collection = ensure_default_collection(current_user.id)
        collection_id = default_collection.id
    
    saved = SavedRecipe(
        user_id=current_user.id,
        recipe_id=recipe_id,
        recipe_name=recipe_name,
        recipe_image=recipe_image,
        collection_id=collection_id
    )
    db.session.add(saved)
    db.session.commit()
    
    flash("Recipe saved to your collection! 📌", "success")
    return redirect(url_for("recipe_detail", recipe_id=recipe_id))


@app.route("/recipes/<int:saved_recipe_id>/move", methods=["POST"])
@login_required
def move_recipe(saved_recipe_id):
    """Move a saved recipe to a different collection."""
    saved_recipe = SavedRecipe.query.get_or_404(saved_recipe_id)
    
    if saved_recipe.user_id != current_user.id:
        flash("You cannot modify another user's recipes.", "danger")
        return redirect(url_for("user_dashboard"))
    
    new_collection_id = request.form.get("collection_id")
    if not new_collection_id:
        flash("Please select a collection.", "warning")
        return redirect(request.referrer or url_for("user_dashboard"))
    
    # Verify new collection belongs to user
    new_collection = Collection.query.get_or_404(new_collection_id)
    if new_collection.user_id != current_user.id:
        flash("Invalid collection.", "danger")
        return redirect(url_for("user_dashboard"))
    
    saved_recipe.collection_id = new_collection_id
    db.session.commit()
    
    flash(f"Recipe moved to '{new_collection.name}'! 📦", "success")
    return redirect(request.referrer or url_for("user_dashboard"))

# -------------------------------------------------
# Entry point
# -------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
