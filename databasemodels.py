from flask import Flask
from flask_sqlalchemy import SQLAlchemy #needsfix????
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

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
    recipe_id = db.Column(db.Integer, nullable=False)  # Spoonacular recipe ID
    recipe_name = db.Column(db.String(200), nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

#to add: shopping list class

