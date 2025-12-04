import requests
from config import Config
import os, requests
from datetime import datetime, timedelta
from databasemodels import RecipeCache, db
BASE = "https://api.spoonacular.com"
API_KEY = Config.SPOONACULAR_API_KEY


#week 5 - modified utils search recipes by ing function to include filters / categorized searching
def search_recipes_by_ingredients(ingredients: str, number: int = 10):
    """Search recipes by ingredients and enrich with detailed info."""
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
        recipes = response.json()
        
        # Enrich each recipe with detailed info (time, price)
        enriched_recipes = []
        for recipe in recipes:
            recipe_id = recipe.get('id')
            
            # Check cache first
            cached = get_recipe_cached(recipe_id)
            if cached:
                # Merge cached data into recipe
                recipe['readyInMinutes'] = cached.get('readyInMinutes', 0)
                recipe['pricePerServing'] = cached.get('pricePerServing', 0)
            
            enriched_recipes.append(recipe)
        
        return enriched_recipes
        
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

def get_recipe_cached(recipe_id: int, force_refresh=False):
    """Fetch recipe info from cache if fresh, otherwise fetch from Spoonacular."""

    cache = RecipeCache.query.filter_by(spoonacular_id=recipe_id).first()

    # If cached within last 7 days
    if cache and not force_refresh:
        if cache.last_fetched and cache.last_fetched > datetime.utcnow() - timedelta(days=7):
            return cache.json_blob

    # 1. Try price breakdown JSON endpoint
    price_url = f"{BASE}/recipes/{recipe_id}/priceBreakdownWidget.json"
    params = {"apiKey": API_KEY}

    try:
        price_response = requests.get(price_url, params=params, timeout=10)

        if price_response.status_code == 200:
            data = price_response.json()
        else:
            # 2. Fallback to recipe information endpoint
            info_url = f"{BASE}/recipes/{recipe_id}/information"
            info_response = requests.get(info_url, params=params, timeout=10)
            info_response.raise_for_status()
            data = info_response.json()

    except requests.exceptions.RequestException as e:
        print(f"[CACHE] Error fetching data: {e}")
        return None

    # Update or create cache
    if not cache:
        cache = RecipeCache(spoonacular_id=recipe_id)
        db.session.add(cache)

    cache.json_blob = data
    cache.price_per_serving = data.get("totalCostPerServing") or data.get("pricePerServing")
    cache.ready_in_minutes = data.get("readyInMinutes")
    cache.last_fetched = datetime.utcnow()

    db.session.commit()
    return data
