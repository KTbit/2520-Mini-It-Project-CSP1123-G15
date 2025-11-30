<<<<<<< HEAD
from flask_sqlalchemy import SQLAlchemy
=======
from flask import Flask
from flask_sqlalchemy import SQLAlchemy #needsfix????
>>>>>>> 65b9ef74ff36e65d62039d53d2ac1714437d849f
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

<<<<<<< HEAD
# Single SQLAlchemy instance, initialised in app.py
db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    saved_recipes = db.relationship("SavedRecipe", backref="user", lazy=True)
    shopping_lists = db.relationship("ShoppingList", backref="user", lazy=True)

    def set_password(self, password: str) -> None:
        """Hash and store the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check a plaintext password against the stored hash."""
        return check_password_hash(self.password_hash, password)


class SavedRecipe(db.Model):
    """Recipes that a user has chosen to save/favourite."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
=======
db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique =True, nullable = False)
    email = db.Column(db.String(120), unique =True, nullable = False)
    password_hash = db.Column(db.String(200), nullable = False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

#admin class to be added later by Lau

#recipe relationships
saved_recipes = db.relationship('SavedRecipe', backref='user', lazy = True)
shopping_lists = db.relationship('ShoppingList', backref='user', lazy = True)
    
def set_password(self, password):
    self.password_hash = generate_password_hash(password)
    
def check_password(self, password):
    return check_password_hash(self.password_hash, password)

#for user saving recipes
class SavedRecipe (db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable = False)
>>>>>>> 65b9ef74ff36e65d62039d53d2ac1714437d849f
    recipe_id = db.Column(db.Integer, nullable=False)  # Spoonacular recipe ID
    recipe_name = db.Column(db.String(200), nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

<<<<<<< HEAD
    def __repr__(self) -> str:
        return f"<SavedRecipe {self.recipe_name!r} for user_id={self.user_id}>"


class ShoppingList(db.Model):
    """Shopping list entries created from recipes for a given user.

    For simplicity, each entry represents one recipe added to the shopping list,
    and stores a JSON-encoded list of ingredient strings.
    """

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    recipe_id = db.Column(db.Integer, nullable=False)
    recipe_name = db.Column(db.String(200), nullable=False)
    ingredients_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def ingredients(self):
        """Return the ingredients as a Python list of strings."""
        import json as _json
        try:
            return _json.loads(self.ingredients_json)
        except Exception:
            return []
=======
#to add: shopping list class

>>>>>>> 65b9ef74ff36e65d62039d53d2ac1714437d849f
