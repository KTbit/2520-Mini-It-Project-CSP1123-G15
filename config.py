import os

class Config:
    """Application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "DEVONLY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", 'sqlite:///recipes_new.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SPOONACULAR_API_KEY = "3d0d6476751b4895b48d0ccb60a7d763"

    # Spoonacular API key (assignment/demo)
    SPOONACULAR_API_KEY = os.environ.get(
        "SPOONACULAR_API_KEY",
        "3d0d6476751b4895b48d0ccb60a7d763"
    )
