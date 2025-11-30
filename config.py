import os
<<<<<<< HEAD

class Config:
    """Application configuration."""
    # In production, override these with environment variables
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///recipes.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Spoonacular API key (for assignment/demo only)
    SPOONACULAR_API_KEY = os.environ.get(
        "SPOONACULAR_API_KEY",
        "3d0d6476751b4895b48d0ccb60a7d763"  # <-- from your original config
    )
=======
import secrets

print(secrets.token_hex(32))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///recipes.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    spoonacular_API_key = '3d0d6476751b4895b48d0ccb60a7d763'


>>>>>>> 65b9ef74ff36e65d62039d53d2ac1714437d849f
