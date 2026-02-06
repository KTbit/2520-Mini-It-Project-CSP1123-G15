from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Single SQLAlchemy instance, initialised in app.py
db = SQLAlchemy()

follows = db.Table(
    'follows',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    collections = db.relationship('Collection', backref='owner', lazy='dynamic')

    followed = db.relationship(
        'User', secondary=follows,
        primaryjoin=(follows.c.follower_id == id),
        secondaryjoin=(follows.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic'
    )

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)
    
    saved_recipes = db.relationship("SavedRecipe", backref="user", lazy=True)
    shopping_lists = db.relationship("ShoppingList", backref="user", lazy=True)
    manual_shopping_items = db.relationship("ManualShoppingItem", backref="user", lazy=True) #manual shopping list


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    spoonacular_id = db.Column(db.Integer)  # recipe id from Spoonacular
    title = db.Column(db.String(300))
    image = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    comments = db.relationship('Comment', backref='post', lazy='dynamic')

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    body = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class RecipeCache(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spoonacular_id = db.Column(db.Integer, unique=True, index=True)
    json_blob = db.Column(db.JSON)  # store fetched JSON (incl. priceBreakdown)
    price_per_serving = db.Column(db.Float)
    ready_in_minutes = db.Column(db.Integer)
    last_fetched = db.Column(db.DateTime, default=datetime.utcnow)



# week 9 - tried to modify existing dashboard feature (more like pinterest; to make it differ from user profile)

class Collection(db.Model):
    """User-generated collections of recipes (like Pinterest boards)"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_default = db.Column(db.Boolean, default=False) #the site automatically creates a board if the user has no previously created ones
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    #Relationship to recipes in this collection
    recipes = db.relationship('SavedRecipe', backref='collection', lazy='dynamic')

    def __repr__(self):
        return f"<Collection {self.name!r}>"


class SavedRecipe(db.Model):
   

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    recipe_id = db.Column(db.Integer, nullable=False)  # Spoonacular recipe ID
    recipe_name = db.Column(db.String(200), nullable=False)
    recipe_image = db.Column(db.String(500))
    collection_id = db.Column(db.Integer, db.ForeignKey('collection.id')) 
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<SavedRecipe {self.recipe_name!r} for user_id={self.user_id}>"

# Added by Salman in Week 5
class ShoppingList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    recipe_id = db.Column(db.Integer, nullable=False)
    recipe_name = db.Column(db.String(200), nullable=False)
    ingredients_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def ingredients(self):
        import json as _json
        try:
            return _json.loads(self.ingredients_json)
        except Exception:
            return []


# Added by Salman in Week 10
class ManualShoppingItem(db.Model):
    """Manual shopping list items added by the user (not tied to a recipe)."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    item_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.String(80), nullable=True)
    notes = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<ManualShoppingItem {self.item_name!r} for user_id={self.user_id}>"