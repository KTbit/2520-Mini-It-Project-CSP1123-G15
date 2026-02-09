import json
import os
import io
from flask import (
    Flask, render_template, request, redirect, url_for, flash, abort, make_response, jsonify, send_file
)
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen import canvas
from io import BytesIO
from functools import wraps

from databasemodels import db, User, SavedRecipe, ShoppingList, Post, Comment, Collection, ManualShoppingItem
from config import Config
from utilities import search_recipes_by_ingredients, get_recipe_details, get_recipe_cached, autocomplete_ingredients

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "user_login"

# USD to MYR conversion rate (update this periodically or use an API)
USD_TO_MYR = 4.50  # Approximate rate, update as needed

@login_manager.user_loader
def load_user(user_id: str):
    try:
        return User.query.get(int(user_id))
    except (TypeError, ValueError):
        return None

# Create DB tables if they do not exist
with app.app_context():
    db.create_all()

# -------------------------------------------------
# ADDED: Helper functions for PDF generation (from groupmate's version)
# -------------------------------------------------
def _logo_path() -> str:
    """Absolute path to the MMU logo used in PDF exports."""
    return os.path.join(app.root_path, "static", "img", "mmu_logo.png")


def _draw_pdf_header(pdf_canvas: canvas.Canvas, width: float, height: float, username: str | None):
    """Draws a consistent header (logo + title + user) on the current page.

    Returns the y position where body content should start.
    """
    # Logo
    logo = _logo_path()
    header_top = height - 30
    if os.path.exists(logo):
        try:
            img = ImageReader(logo)
            iw, ih = img.getSize()
            # Fit logo nicely in the header
            target_h = 40
            target_w = max(1, int((iw / max(1, ih)) * target_h))
            pdf_canvas.drawImage(
                img,
                50,
                header_top - target_h,
                width=target_w,
                height=target_h,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception:
            # If image fails to load, continue without logo.
            pass

    # Title + user
    y = height - 90
    pdf_canvas.setFont("Helvetica-Bold", 16)
    pdf_canvas.drawString(50, y, "Shopping List")
    pdf_canvas.setFont("Helvetica", 10)
    y -= 18
    if username:
        pdf_canvas.drawString(50, y, f"User: {username}")
        y -= 22
    else:
        y -= 10

    # Divider line
    pdf_canvas.setLineWidth(0.6)
    pdf_canvas.line(50, y, width - 50, y)
    y -= 22
    return y


# Helper function for currency conversion
def convert_to_myr(price_in_cents):
    """Convert Spoonacular price (USD cents) to Malaysian Ringgit"""
    if not price_in_cents:
        return None
    usd_dollars = price_in_cents / 100
    return usd_dollars * USD_TO_MYR

@app.route("/")
def index():
    recent_posts = Post.query.order_by(Post.created_at.desc()).limit(6).all()
    return render_template("index.html", recent_posts=recent_posts)

@app.route("/recipes/browse")
def recipe_browse():
    """Enhanced recipe browsing with category filters."""
    ingredients = request.args.get("ingredients", "", type=str).strip()
    
    # Get filter parameters
    cuisine = request.args.get("cuisine", "", type=str).strip()
    diet = request.args.get("diet", "", type=str).strip()
    meal_type = request.args.get("type", "", type=str).strip()
    max_time = request.args.get("maxReadyTime", "", type=str).strip()
    max_price = request.args.get("maxPrice", "", type=str).strip()
    sort_by = request.args.get("sort", "", type=str).strip()
    
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
    
    # Convert MYR to USD cents for API
    if max_price:
        try:
            myr_price = float(max_price)
            usd_price = myr_price / USD_TO_MYR
            filters['maxPrice'] = int(usd_price * 100)  # Convert to cents
        except ValueError:
            pass
    
    if sort_by:
        filters['sort'] = sort_by
    
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
        'maxPrice': max_price,
        'sort': sort_by,
    }
    
    return render_template(
        "recipe_section/recipebrowse.html",
        recipes=recipes,
        active_filters=active_filters,
    )

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

    is_saved = False
    user_collections = []
    if current_user.is_authenticated:
        is_saved = (
            SavedRecipe.query.filter_by(
                user_id=current_user.id, recipe_id=recipe_id
            ).first()
            is not None
        )
        user_collections = Collection.query.filter_by(
            user_id=current_user.id
        ).order_by(Collection.is_default.desc(), Collection.created_at.desc()).all()

    # Extract pricing information and convert to MYR 
    price_per_serving = details.get('pricePerServing')
    servings = details.get('servings', 1)
    
    price_formatted = None
    total_price_formatted = None
    
    if price_per_serving:
        price_myr = convert_to_myr(price_per_serving)
        total_price_myr = price_myr * servings
        
        price_formatted = f"RM {price_myr:.2f}"
        total_price_formatted = f"RM {total_price_myr:.2f}"

    return render_template(
        "recipe_section/recipedetail.html",
        recipe=details,
        is_saved=is_saved,
        user_collections=user_collections,
        price_per_serving=price_formatted,
        total_price=total_price_formatted,
        servings=servings,
    )


# WEEK 2 - Authenticate user route - written by Siti 
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

# Login route
@app.route("/login", methods=["GET", "POST"])
def user_login():
    if current_user.is_authenticated:
        return redirect(url_for("profile", user_id=current_user.id))  # CHANGED: redirect to profile

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash("Invalid username or password.", "danger")
            return redirect(url_for("user_login"))

        login_user(user)
        flash("Logged in successfully.", "success")
        return redirect(url_for("profile", user_id=user.id))  # CHANGED: redirect to profile

    return render_template("user/user_login.html")

# Logout route
@app.route("/logout")
@login_required
def user_logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))

# WEEK 4 - Added Saving / Unsaving recipes route - by Siti

@app.route("/recipes/<int:recipe_id>/unsave", methods=["POST"]) #Unsaving route
@login_required
def unsave_recipe(recipe_id: int):
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

# WEEK 5 - Created and added user post creation / deletion route EDIT: fully finished by Week 8; by Siti
@app.route('/posts/create', methods=['POST'])
@login_required
def create_post():
    recipe_id = request.form.get('recipe_id')
    
    if not recipe_id:
        flash("No recipe specified!", "danger")
        return redirect(url_for('index'))
    
    recipe = get_recipe_cached(int(recipe_id))
    
    if not recipe:
        flash("Could not fetch recipe details!", "danger")
        return redirect(url_for('index'))
    
    existing = Post.query.filter_by(
        user_id=current_user.id, 
        spoonacular_id=int(recipe_id)
    ).first()
    
    if existing:
        flash("You've already shared this recipe!", "info")
        return redirect(url_for('post_view', post_id=existing.id))
    
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
    db.session.delete(p)
    db.session.commit()
    flash("Post deleted.", "info")
    return redirect(url_for('index'))

@app.route('/posts')
def posts_feed():
    if current_user.is_authenticated:
        posts = Post.query.order_by(Post.created_at.desc()).limit(50).all()
    else:
        # Show a preview of recent posts to entice people to sign up
        posts = Post.query.order_by(Post.created_at.desc()).limit(20).all()
    
    return render_template('posts_feed.html', posts=posts)

@app.route('/posts/<int:post_id>')
def post_view(post_id):
    post = Post.query.get_or_404(post_id)
    recipe = get_recipe_cached(post.spoonacular_id)
    
    # ADDED: Convert price to MYR for post view (was missing before)
    price_formatted = None
    total_price_formatted = None
    servings = 1
    
    if recipe:
        price_per_serving = recipe.get('pricePerServing')
        servings = recipe.get('servings', 1)
        
        if price_per_serving:
            price_myr = convert_to_myr(price_per_serving)
            total_price_myr = price_myr * servings
            
            price_formatted = f"RM {price_myr:.2f}"
            total_price_formatted = f"RM {total_price_myr:.2f}"
    
    # Pass Comment model to template
    return render_template(
        'post_view.html', 
        post=post, 
        recipe=recipe, 
        Comment=Comment,
        price_per_serving=price_formatted,
        total_price=total_price_formatted,
        servings=servings
    )

@app.route('/profile/<int:user_id>') 
def profile(user_id):
    user = User.query.get_or_404(user_id)
    posts = Post.query.filter_by(user_id=user_id).order_by(Post.created_at.desc()).all()
    
    is_following = False
    if current_user.is_authenticated:
        is_following = current_user.followed.filter_by(id=user_id).first() is not None
    
    # Only show if viewing own profile
    collections = []
    if current_user.is_authenticated and current_user.id == user_id:
        # Viewing own profile - show all collections
        collections = Collection.query.filter_by(user_id=user_id).order_by(
            Collection.is_default.desc(), 
            Collection.created_at.desc()
        ).all()
    
    return render_template(
        'user/profile.html', 
        user=user, 
        posts=posts, 
        is_following=is_following,
        collections=collections  # ADDED
    )

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

# WEEK 6 - Comment route added EDIT: Finished + Debugged by Week 9 - by Siti
@app.route('/posts/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
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

# Comment deletion route
@app.route('/posts/<int:post_id>/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(post_id, comment_id):
    comment = Comment.query.get_or_404(comment_id)
    
    if comment.user_id != current_user.id and not current_user.is_admin:
        flash("You can only delete your own comments!", "danger")
        return redirect(url_for('post_view', post_id=post_id))
    
    db.session.delete(comment)
    db.session.commit()
    
    flash("Comment deleted.", "info")
    return redirect(url_for('post_view', post_id=post_id))

# WEEK 4 - Salman wrote and finished Shopping List Routes
@app.route("/shopping-list")
@login_required
def shopping_list():
    items = ShoppingList.query.filter_by(user_id=current_user.id).order_by(
        ShoppingList.created_at.desc()
    ).all()
    
    # ADDED: Query manual shopping items (from groupmate's version)
    manual_items = ManualShoppingItem.query.filter_by(user_id=current_user.id).order_by(
        ManualShoppingItem.created_at.desc()
    ).all()
    
    # Calculate total cost in MYR - added by Siti
    total_cost_myr = 0
    for item in items:
        recipe = get_recipe_cached(item.recipe_id)
        if recipe and recipe.get('pricePerServing'):
            price_myr = convert_to_myr(recipe['pricePerServing'])
            servings = recipe.get('servings', 1)
            total_cost_myr += price_myr * servings
    
    return render_template(
        "user/shopping_list.html", 
        items=items,
        manual_items=manual_items,  # ADDED: Pass manual items to template
        total_cost=f"RM {total_cost_myr:.2f}"
    )

@app.route("/recipes/<int:recipe_id>/add-to-shopping-list", methods=["POST"])
@login_required
def add_to_shopping_list(recipe_id: int):
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

# REMOVED DUPLICATE: This function was defined twice in original file
# Kept only one instance below in the proper location
@app.route("/shopping-list/<int:item_id>/remove", methods=["POST"])
@login_required
def remove_from_shopping_list(item_id: int):
    item = ShoppingList.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        flash("You cannot modify another user's shopping list.", "danger")
        return redirect(url_for("shopping_list"))

    db.session.delete(item)
    db.session.commit()
    flash("Item removed from your shopping list.", "success")
    return redirect(url_for("shopping_list"))

# -------------------------------------------------
# ADDED: Manual Shopping List Routes (from groupmate's version)
# -------------------------------------------------
@app.route("/shopping-list/manual/add", methods=["POST"])
@login_required
def shopping_list_manual_add():
    """Add a manual shopping item (not tied to a recipe)"""
    name = (request.form.get("item_name") or "").strip()
    quantity = (request.form.get("quantity") or "").strip()
    notes = (request.form.get("notes") or "").strip()

    if not name:
        flash("Please enter an item name.", "warning")
        return redirect(url_for("shopping_list"))

    item = ManualShoppingItem(
        user_id=current_user.id,
        item_name=name,
        quantity=quantity or None,
        notes=notes or None,
    )
    db.session.add(item)
    db.session.commit()
    flash("Manual item added to your shopping list.", "success")
    return redirect(url_for("shopping_list"))


@app.route("/shopping-list/manual/<int:item_id>/remove", methods=["POST"])
@login_required
def shopping_list_manual_remove(item_id: int):
    """Remove a manual shopping item"""
    item = ManualShoppingItem.query.filter_by(id=item_id, user_id=current_user.id).first()
    if not item:
        flash("Item not found.", "warning")
        return redirect(url_for("shopping_list"))
    db.session.delete(item)
    db.session.commit()
    flash("Manual item removed.", "success")
    return redirect(url_for("shopping_list"))

# -------------------------------------------------
# WEEK 5 - Shopping List PDF export 
# MODIFIED: Enhanced with logo header from groupmate's version
# -------------------------------------------------
@app.route("/shopping-list/pdf")
@login_required
def shopping_list_pdf():
    items = ShoppingList.query.filter_by(user_id=current_user.id).order_by(
        ShoppingList.created_at.desc()
    ).all()
    
    # ADDED: Get manual items for PDF export
    manual_items = ManualShoppingItem.query.filter_by(user_id=current_user.id).order_by(
        ManualShoppingItem.created_at.asc()
    ).all()
    
    if not items and not manual_items:
        flash('Your shopping list is empty!', 'info')
        return redirect(url_for('shopping_list'))
    
    # MODIFIED: Use A4 page size and canvas (from groupmate's version for better logo support)
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # ADDED: Use improved header function with logo (from groupmate's version)
    y = _draw_pdf_header(pdf, width, height, getattr(current_user, "username", None))
    
    # Recipe-based shopping list items
    if items:
        for item in items:
            if y < 80:
                pdf.showPage()
                y = _draw_pdf_header(pdf, width, height, getattr(current_user, "username", None))
            
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(50, y, f"- {item.recipe_name}")
            y -= 18
            pdf.setFont("Helvetica", 10)
            
            for ing in item.ingredients():
                text = f"• {ing}"
                max_chars = 90
                lines = [text[i:i+max_chars] for i in range(0, len(text), max_chars)]
                for line in lines:
                    if y < 60:
                        pdf.showPage()
                        y = _draw_pdf_header(pdf, width, height, getattr(current_user, "username", None))
                    pdf.drawString(70, y, line)
                    y -= 14
            y -= 10

    # ADDED: Manual items section in PDF (from groupmate's version)
    if manual_items:
        if y < 120:
            pdf.showPage()
            y = _draw_pdf_header(pdf, width, height, getattr(current_user, "username", None))
        
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(50, y, "Manual Items")
        y -= 18
        pdf.setFont("Helvetica", 11)
        
        for mi in manual_items:
            if y < 80:
                pdf.showPage()
                y = _draw_pdf_header(pdf, width, height, getattr(current_user, "username", None))
                pdf.setFont("Helvetica", 11)
            
            line = f"• {mi.item_name}"
            if mi.quantity:
                line += f" ({mi.quantity})"
            if mi.notes:
                line += f" — {mi.notes}"
            pdf.drawString(50, y, line[:110])
            y -= 14
    
    pdf.save()
    buffer.seek(0)
    
    # MODIFIED: Use send_file with download_name parameter
    filename = f"shopping_list_{current_user.username}.pdf"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )

# WEEK 3 - Added Admin decorator / route(s) - by Siti 
# EDIT - WEEK 11: Salman fully reworked all of the admin routes in Week 11
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

# Week 4 - Week 5; finished with admin dashboard route + debugging, helped by Salman - Siti
# EDIT - WEEK 11: Salman fully reworked admin dashboard route
@app.route("/admin/dashboard")
@login_required
@admin_required
def admin_dashboard():
    users = User.query.order_by(User.created_at.desc()).all()
    posts = Post.query.order_by(Post.created_at.desc()).limit(20).all()
    comments = Comment.query.order_by(Comment.created_at.desc()).limit(20).all()
    
    stats = {
        'total_users': User.query.count(),
        'total_posts': Post.query.count(),
        'total_comments': Comment.query.count(),
        'total_collections': Collection.query.count(),
    }
    
    return render_template(
        "admin/admin_dashboard.html", 
        users=users, 
        posts=posts,
        comments=comments,
        stats=stats
    )

# Admin - user deletion feature; fully debugged in Week 8; during small admin HTML page rework - Siti
# EDIT - WEEK 11: Salman fully debugged + reworked the code for this entire part below
# FIXED: Prevent IntegrityError by deleting related data first
@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def admin_delete_user(user_id: int):
    user = User.query.get_or_404(user_id)
    
    if user.is_admin:
        flash("Cannot delete admin users.", "danger")
        return redirect(url_for('admin_dashboard'))
    
    reason = request.form.get('reason', 'No reason provided')
    
    # Log the deletion (you could store this in a separate table)
    print(f"[ADMIN DELETE] User '{user.username}' deleted by {current_user.username}. Reason: {reason}")
    
    # Delete all related data BEFORE deleting the user to prevent IntegrityError
    # Delete user's collections 
    Collection.query.filter_by(user_id=user_id).delete()
    
    # Delete user's saved recipes (if any remain)
    SavedRecipe.query.filter_by(user_id=user_id).delete()
    
    # Delete user's shopping lists
    ShoppingList.query.filter_by(user_id=user_id).delete()
    
    # Delete user's manual shopping items
    ManualShoppingItem.query.filter_by(user_id=user_id).delete()
    
    # Delete user's posts
    Post.query.filter_by(user_id=user_id).delete()
    
    # Delete user's comments
    Comment.query.filter_by(user_id=user_id).delete()
    
    # Now delete the user itself
    db.session.delete(user)
    db.session.commit()
    
    flash(f"User '{user.username}' has been deleted. Reason: {reason}", "success")
    return redirect(url_for('admin_dashboard'))

# Admin post deletion feature + reason in doing so // added in Week 10 - 11 during (2nd) admin feature rework - done by both Siti, Salman
@app.route("/admin/posts/<int:post_id>/delete", methods=["POST"])
@login_required
@admin_required
def admin_delete_post(post_id: int):
    post = Post.query.get_or_404(post_id)
    reason = request.form.get('reason', 'No reason provided')
    
    print(f"[ADMIN DELETE] Post #{post.id} by {post.author.username} deleted. Reason: {reason}")
    
    db.session.delete(post)
    db.session.commit()
    flash(f"Post deleted. Reason: {reason}", "success")
    return redirect(url_for('admin_dashboard'))

# Admin comment deletion feature added in Week 10 - 11 during (2nd) admin feature rework - done by both Siti, Salman
@app.route("/admin/comments/<int:comment_id>/delete", methods=["POST"])
@login_required
@admin_required
def admin_delete_comment(comment_id: int):
    comment = Comment.query.get_or_404(comment_id)
    reason = request.form.get('reason', 'No reason provided')
    
    print(f"[ADMIN DELETE] Comment #{comment.id} by {comment.author.username} deleted. Reason: {reason}")
    
    db.session.delete(comment)
    db.session.commit()
    flash(f"Comment deleted. Reason: {reason}", "success")
    return redirect(url_for('admin_dashboard'))

# WEEK 4 - 5 : Added Collection routes for users to save / unsave recipes to
def ensure_default_collection(user_id):
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

# WEEK 3 - Added User dashboard route- Siti
# EDIT: Reworked in Week 9; Salman helped in identifying errors
@app.route("/dashboard")
@login_required
def user_dashboard():
    ensure_default_collection(current_user.id)
    collections = Collection.query.filter_by(user_id=current_user.id).order_by(
        Collection.is_default.desc(),
        Collection.created_at.desc()
    ).all()
    return render_template("user/userdashboard.html", collections=collections)

# Collections route - Siti
@app.route("/collections/create", methods=["POST"])
@login_required
def create_collection():
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
    
    flash(f"Collection '{name}' created!", "success")
    return redirect(url_for("user_dashboard"))

# Collection authentication - added in Week 9 rework - Siti
@app.route("/collections/<int:collection_id>")
@login_required
def view_collection(collection_id):
    collection = Collection.query.get_or_404(collection_id)
    
    if collection.user_id != current_user.id:
        flash("You don't have permission to view this collection.", "danger")
        return redirect(url_for("user_dashboard"))
    
    recipes = collection.recipes.order_by(SavedRecipe.saved_at.desc()).all()
    return render_template("user/collection_view.html", collection=collection, recipes=recipes)

# Collection authentication - added in Week 9 rework - Siti
@app.route("/collections/<int:collection_id>/edit", methods=["POST"])
@login_required
def edit_collection(collection_id):
    collection = Collection.query.get_or_404(collection_id)
    
    if collection.user_id != current_user.id:
        flash("You cannot edit another user's collection.", "danger")
        return redirect(url_for("user_dashboard"))
    
    # CHANGED: Allow editing default collection's name/description
    # (Removed the is_default check so users can customize "My Recipes")
    
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    
    if not name:
        flash("Collection name cannot be empty.", "danger")
        return redirect(url_for("user_dashboard"))
    
    collection.name = name
    collection.description = description if description else None
    db.session.commit()
    
    flash("Collection updated!", "success")
    return redirect(url_for("user_dashboard"))

# Collection deletion route - finished by Week 5 - Siti
# FIXED: Properly move recipes to default collection before deletion
@app.route("/collections/<int:collection_id>/delete", methods=["POST"])
@login_required
def delete_collection(collection_id):
    collection = Collection.query.get_or_404(collection_id)
    
    if collection.user_id != current_user.id:
        flash("You cannot delete another user's collection.", "danger")
        return redirect(url_for("user_dashboard"))
    
    
    # FIXED: Properly move recipes to default collection
    default_collection = ensure_default_collection(current_user.id)
    
    # Move all recipes from this collection to the default collection
    recipes_to_move = SavedRecipe.query.filter_by(collection_id=collection_id).all()
    for recipe in recipes_to_move:
        recipe.collection_id = default_collection.id
    
    # Commit the recipe moves first
    db.session.commit()
    
    # Now delete the empty collection
    db.session.delete(collection)
    db.session.commit()
    
    flash(f"Collection '{collection.name}' deleted. {len(recipes_to_move)} recipe(s) moved to 'My Recipes'.", "info")
    return redirect(url_for("user_dashboard"))

# MOVED SAVING FEATURE HERE DURING DEBUGGING + Reworked in Week 9 - Siti
# REMOVED DUPLICATE: This was the second definition of save_recipe - kept only this one
@app.route("/recipes/<int:recipe_id>/save", methods=["POST"])
@login_required
def save_recipe(recipe_id: int):
    recipe_name = request.form.get("recipe_name", "").strip() or "Recipe"
    recipe_image = request.form.get("recipe_image", "").strip()
    collection_id = request.form.get("collection_id")
    
    existing = SavedRecipe.query.filter_by(
        user_id=current_user.id, recipe_id=recipe_id
    ).first()
    if existing:
        flash("Recipe already in your saved list.", "info")
        return redirect(url_for("recipe_detail", recipe_id=recipe_id))
    
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
    
    flash("Recipe saved to your collection!", "success")
    return redirect(url_for("recipe_detail", recipe_id=recipe_id))

# WEEK 9 - Salman helped write this part for Collection Rework 
@app.route("/recipes/<int:saved_recipe_id>/move", methods=["POST"])
@login_required
def move_recipe(saved_recipe_id):
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
    
    flash(f"Recipe moved to '{new_collection.name}'!", "success")
    return redirect(request.referrer or url_for("user_dashboard"))

# New save_and_create route for JS in recipedetail.html - Siti 
@app.route("/collections/create-and-save", methods=["POST"])
@login_required
def create_collection_and_save_recipe():
    """
    Combined route: Creates a new collection AND saves a recipe to it in one request.
    This is what the modal JavaScript is trying to call.
    
    Expected JSON payload:
    {
        "name": "Collection Name",
        "description": "Optional description",
        "recipe_id": 123,
        "recipe_name": "Recipe Title",
        "recipe_image": "http://..."
    }
    """
    try:
        # Get JSON data from the request
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        # Extract and validate collection data
        collection_name = (data.get('name') or '').strip()
        collection_description = (data.get('description') or '').strip()
        
        if not collection_name:
            return jsonify({
                'success': False,
                'message': 'Collection name is required'
            }), 400
        
        if len(collection_name) > 100:
            return jsonify({
                'success': False,
                'message': 'Collection name is too long (max 100 characters)'
            }), 400
        
        # Extract recipe data
        recipe_id = data.get('recipe_id')
        recipe_name = (data.get('recipe_name') or 'Recipe').strip()
        recipe_image = (data.get('recipe_image') or '').strip()
        
        if not recipe_id:
            return jsonify({
                'success': False,
                'message': 'Recipe ID is required'
            }), 400
        
        try:
            recipe_id = int(recipe_id)
        except (TypeError, ValueError):
            return jsonify({
                'success': False,
                'message': 'Invalid recipe ID'
            }), 400
        
        # Check if recipe is already saved
        existing_recipe = SavedRecipe.query.filter_by(
            user_id=current_user.id,
            recipe_id=recipe_id
        ).first()
        
        if existing_recipe:
            return jsonify({
                'success': False,
                'message': 'This recipe is already in your saved list'
            }), 400
        
        # STEP 1: Create the new collection
        new_collection = Collection(
            user_id=current_user.id,
            name=collection_name,
            description=collection_description if collection_description else None,
            is_default=False
        )
        
        db.session.add(new_collection)
        db.session.flush()  # Get the collection ID without committing yet
        
        # STEP 2: Save the recipe to the new collection
        saved_recipe = SavedRecipe(
            user_id=current_user.id,
            recipe_id=recipe_id,
            recipe_name=recipe_name,
            recipe_image=recipe_image,
            collection_id=new_collection.id
        )
        
        db.session.add(saved_recipe)
        
        # STEP 3: Commit both operations together
        db.session.commit()
        
        # Success!
        return jsonify({
            'success': True,
            'message': f'Collection "{collection_name}" created and recipe saved!',
            'collection_id': new_collection.id,
            'collection_name': collection_name
        }), 201
        
    except Exception as e:
        # Rollback on error
        db.session.rollback()
        print(f"[ERROR] create_collection_and_save_recipe: {str(e)}")
        
        return jsonify({
            'success': False,
            'message': 'An error occurred. Please try again.'
        }), 500


# WEEK 6 - 7 : Salman fully wrote and debugged Chatbot route ; merged by the end of Week 7
@app.route("/chatbot", methods=["POST"])
def chatbot():
    """
    Simple recipe chatbot that helps users search for recipes.
    Uses keyword matching to understand user intent.
    """
    try:
        data = request.get_json()
        user_message = data.get('message', '').lower().strip()
        
        # If user says "help", show available commands
        if 'help' in user_message:
            return jsonify({
                'reply': '''Here's what I can help you with:
                
**Search by ingredients:** "find recipes with chicken and rice"
**Search by cuisine:** "show me italian recipes" or "mexican food"
**Search by diet:** "vegan recipes" or "vegetarian meals"
**Quick meals:** "quick recipes" or "fast meals"
**Get a random suggestion:** "suggest something" or "surprise me"

Just tell me what you're looking for!'''
            })
        
        # Pattern matching for different types of requests
        reply = ""
        
        # Check if user is asking for recipes with specific ingredients
        # Patterns: "find recipes with X", "recipes with X", "cook with X", "use X"
        if any(phrase in user_message for phrase in ['find recipes with', 'recipes with', 'cook with', 'use ', 'have ']):
            # Extract ingredients after the trigger phrase
            # This is a simple extraction - just takes everything after the trigger 
            ingredients = user_message
            for phrase in ['find recipes with', 'recipes with', 'cook with', 'i have', 'use']:
                if phrase in ingredients:
                    ingredients = ingredients.split(phrase, 1)[1].strip()
                    break
            
            # Remove common filler words
            ingredients = ingredients.replace(' and ', ', ').replace('some', '').strip()
            
            reply = f'''Great! Let me help you find recipes with **{ingredients}**.

Click here to search: /recipes/browse?ingredients={ingredients.replace(' ', '+')}

Or you can visit the Search Recipes page and enter: {ingredients}'''
        
        # Check if user is asking for cuisine-specific recipes
        # Patterns: "italian", "mexican", "asian", etc.
        elif any(cuisine in user_message for cuisine in ['italian', 'mexican', 'asian', 'chinese', 'indian', 'japanese']):
            cuisine = None
            if 'italian' in user_message:
                cuisine = 'italian'
            elif 'mexican' in user_message:
                cuisine = 'mexican'
            elif 'asian' in user_message:
                cuisine = 'asian'
            elif 'chinese' in user_message:
                cuisine = 'chinese'
            elif 'indian' in user_message:
                cuisine = 'indian'
            elif 'japanese' in user_message:
                cuisine = 'japanese'
            
            reply = f'''I can show you delicious **{cuisine.title()}** recipes! 🍜

Click here: /recipes/browse?cuisine={cuisine}

Or visit Search Recipes and filter by {cuisine.title()} cuisine.'''
        
        # Check if user is asking for diet-specific recipes
        elif any(diet in user_message for diet in ['vegan', 'vegetarian', 'gluten free', 'gluten-free']):
            diet = None
            if 'vegan' in user_message:
                diet = 'vegan'
            elif 'vegetarian' in user_message:
                diet = 'vegetarian'
            elif 'gluten' in user_message:
                diet = 'gluten free'
            
            reply = f'''Looking for **{diet}** recipes? I've got you covered! 🌱

Click here: /recipes/browse?diet={diet.replace(' ', '+')}

Or use the diet filter on the Search Recipes page.'''
        
        # Check if user wants quick/fast recipes
        elif any(word in user_message for word in ['quick', 'fast', 'easy', '15 min', '30 min']):
            time_limit = '30'  # Default to 30 minutes
            if '15' in user_message:
                time_limit = '15'
            
            reply = f'''Here are recipes ready in **{time_limit} minutes or less**! ⚡

Click here: /recipes/browse?maxReadyTime={time_limit}

Perfect for busy days!'''
        
        # Check if user wants breakfast recipes
        elif any(word in user_message for word in ['breakfast', 'morning', 'brunch']):
            reply = '''Good morning! Here are some **breakfast** ideas: 🌅

Click here: /recipes/browse?type=breakfast

Start your day delicious!'''
        
        # Check if user wants dessert recipes
        elif any(word in user_message for word in ['dessert', 'sweet', 'cake', 'cookie']):
            reply = '''Sweet tooth? Here are some **dessert** recipes: 🍰

Click here: /recipes/browse?type=dessert

Enjoy!'''
        
        # Random suggestion - just send them to browse
        elif any(phrase in user_message for phrase in ['suggest', 'surprise', 'random', 'what should i', 'recommend']):
            reply = '''How about exploring our recipe collection? 

**Browse all recipes:** /recipes/browse

Or try these quick links:
- **15-minute meals:** /recipes/browse?maxReadyTime=15
- **Vegetarian:** /recipes/browse?diet=vegetarian
- **Italian:** /recipes/browse?cuisine=italian

Happy cooking! 👨‍🍳'''
        
        # If we couldn't match any pattern, give a helpful default response
        else:
            reply = f'''I'm not quite sure what you're looking for, but I'm here to help! 

Try asking me things like:
- "Find recipes with chicken and tomato"
- "Show me vegan recipes"
- "Quick Italian meals"
- "Breakfast ideas"

Or type **help** to see all I can do! 💬'''
        
        return jsonify({'reply': reply})
    
    except Exception as e:
        # Log the error for debugging
        print(f"[Chatbot Error]: {str(e)}")
        return jsonify({
            'reply': 'Sorry, I encountered an error. Please try rephrasing your question or type **help** for examples!'
        }), 500


if __name__ == "__main__":
    app.run(debug=True)