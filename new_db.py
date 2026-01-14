# To create a fresh database with any new columns (namely because to delete the old outdated database that doesn't have the 'recipe_image' column in it.)

import os
from app import app, db
from databasemodels import User, Collection

# Delete old database
db_path = 'instance/recipes.db'
if os.path.exists(db_path):
    os.remove(db_path)
    print("Deleted old database.")

# Create new database with all tables
with app.app_context():
    db.create_all()
    print("New database created.")
    
   