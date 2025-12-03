import os

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
