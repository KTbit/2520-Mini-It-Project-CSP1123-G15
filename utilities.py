import requests
from config import Config

def search_recipes_by_ingredients(ingredients, number=10):
    """Search recipes by ingredients using Spoonacular API"""
    url = "https://api.spoonacular.com/recipes/findByIngredients"
    params = {
        "apiKey": Config.SPOONACULAR_API_KEY,
        "ingredients": ingredients,
        "number": number,
        "ranking": 1,
        "ignorePantry": True
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
        return []

def get_recipe_details(recipe_id):
    """Get detailed recipe information including nutrition"""
    url = f"https://api.spoonacular.com/recipes/{recipe_id}/information"
    params = {
        "apiKey": Config.SPOONACULAR_API_KEY,
        "includeNutrition": True
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
        return None