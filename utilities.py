import requests
from config import Config

<<<<<<< HEAD

def search_recipes_by_ingredients(ingredients: str, number: int = 10):
    """Search recipes by ingredients using the Spoonacular API.

    Parameters
    ----------
    ingredients : str
        Comma-separated list of ingredients, e.g. "egg,tomato,cheese".
    number : int
        Max number of recipes to return.

    Returns
    -------
    list[dict]
        A list of recipe objects from Spoonacular, or [] on failure.
    """
=======
def search_recipes_by_ingredients(ingredients, number=10):
    """Search recipes by ingredients using Spoonacular API"""
>>>>>>> 65b9ef74ff36e65d62039d53d2ac1714437d849f
    url = "https://api.spoonacular.com/recipes/findByIngredients"
    params = {
        "apiKey": Config.SPOONACULAR_API_KEY,
        "ingredients": ingredients,
        "number": number,
        "ranking": 1,
<<<<<<< HEAD
        "ignorePantry": True,
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as exc:
        print(f"[Spoonacular] Error searching recipes: {exc}")
        return []


def get_recipe_details(recipe_id: int):
    """Get detailed recipe information including nutrition.

    Returns a dict on success, or None on failure.
    """
    url = f"https://api.spoonacular.com/recipes/{recipe_id}/information"
    params = {
        "apiKey": Config.SPOONACULAR_API_KEY,
        "includeNutrition": True,
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as exc:
        print(f"[Spoonacular] Error getting recipe details: {exc}")
        return None
=======
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
>>>>>>> 65b9ef74ff36e65d62039d53d2ac1714437d849f
