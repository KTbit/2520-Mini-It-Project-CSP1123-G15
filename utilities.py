import requests
from config import Config


def search_recipes_by_ingredients(ingredients: str, number: int = 10):
    url = "https://api.spoonacular.com/recipes/findByIngredients"
    params = {
        "apiKey": Config.SPOONACULAR_API_KEY,
        "ingredients": ingredients,
        "number": number,
        "ranking": 1,
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
