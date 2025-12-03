import json
import io

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file,
)
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from databasemodels import db, User, SavedRecipe, ShoppingList
from config import Config
from utilities import search_recipes_by_ingredients, get_recipe_details


app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "user_login"


@login_manager.user_loader
def load_user(user_id: str):
    try:
        return User.query.get(int(user_id))
    except (TypeError, ValueError):
        return None


with app.app_context():
    db.create_all()


# -------------------------------------------------
# Public routes
# -------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/recipes/browse")
def recipe_browse():
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
    details = get_recipe_details(recipe_id)
    if details is None:
        flash("Could not load recipe details. Please try again later.", "danger")
        return redirect(url_for("index"))

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
# Authentication
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


@app.route("/dashboard")
@login_required
def user_dashboard():
    saved = SavedRecipe.query.filter_by(user_id=current_user.id).all()
    return render_template("user/userdashboard.html", saved_recipes=saved)


# -------------------------------------------------
# Saved recipes
# -------------------------------------------------
@app.route("/recipes/<int:recipe_id>/save", methods=["POST"])
@login_required
def save_recipe(recipe_id: int):
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
# Shopping List (Week 4)
# -------------------------------------------------
@app.route("/shopping-list")
@login_required
def shopping_list():
    items = ShoppingList.query.filter_by(user_id=current_user.id).order_by(
        ShoppingList.created_at.desc()
    ).all()
    return render_template("user/shopping_list.html", items=items)


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
# Week 5: Shopping List PDF export
# -------------------------------------------------
@app.route("/shopping-list/pdf")
@login_required
def shopping_list_pdf():
    items = ShoppingList.query.filter_by(user_id=current_user.id).order_by(
        ShoppingList.created_at.asc()
    ).all()

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "Shopping List")
    pdf.setFont("Helvetica", 10)
    y -= 20
    pdf.drawString(50, y, f"User: {current_user.username}")
    y -= 30

    if not items:
        pdf.drawString(50, y, "Your shopping list is currently empty.")
    else:
        for item in items:
            if y < 80:
                pdf.showPage()
                y = height - 50
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
                        y = height - 50
                    pdf.drawString(70, y, line)
                    y -= 14
            y -= 10

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    filename = "shopping_list.pdf"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )


# -------------------------------------------------
# Admin (Week 6 skeleton, already in place)
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


if __name__ == "__main__":
    app.run(debug=True)
