import os
import secrets

print(secrets.token_hex(32))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///recipes.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    spoonacular_API_key = '3d0d6476751b4895b48d0ccb60a7d763'


