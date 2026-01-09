import requests
from config import Config


def search_recipes_by_ingredients(ingredients: str, number: int = 10, **filters):
    """
    Search recipes by ingredients with optional category filters.
    
    Additional filter parameters:
    - cuisine: str (e.g., 'italian', 'mexican', 'asian')
    - diet: str (e.g., 'vegetarian', 'vegan', 'gluten free')
    - type: str (e.g., 'main course', 'dessert', 'breakfast')
    - maxReadyTime: int (max cooking time in minutes)
    - intolerances: str (e.g., 'dairy', 'egg', 'gluten')
    """
    url = "https://api.spoonacular.com/recipes/complexSearch"
    
    params = {
        "apiKey": Config.SPOONACULAR_API_KEY,
        "includeIngredients": ingredients,
        "number": number,
        "addRecipeInformation": True,
        "fillIngredients": True,
        "ignorePantry": True,
        "sort": "min-missing-ingredients",
    }
    
    # Add category filters if provided
    if filters.get('cuisine'):
        params['cuisine'] = filters['cuisine']
    
    if filters.get('diet'):
        params['diet'] = filters['diet']
    
    if filters.get('type'):
        params['type'] = filters['type']
    
    if filters.get('maxReadyTime'):
        params['maxReadyTime'] = filters['maxReadyTime']
    
    if filters.get('intolerances'):
        params['intolerances'] = filters['intolerances']

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        # Return the results array
        return data.get('results', [])
    except requests.exceptions.RequestException as exc:
        print(f"[Spoonacular] Error searching recipes: {exc}")
        return []


def get_recipe_details(recipe_id: int):
    """Fetch detailed information about a specific recipe."""
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


def search_recipes_advanced(query: str = "", **filters):
    """
    Advanced recipe search supporting both text queries and filters.
    Useful for pure category browsing without specific ingredients.
    
    Parameters:
    - query: str (general search term)
    - cuisine, diet, type, maxReadyTime, intolerances (same as above)
    """
    url = "https://api.spoonacular.com/recipes/complexSearch"
    
    params = {
        "apiKey": Config.SPOONACULAR_API_KEY,
        "number": filters.get('number', 12),
        "addRecipeInformation": True,
    }
    
    if query:
        params['query'] = query
    
    # Add all filters
    for key in ['cuisine', 'diet', 'type', 'maxReadyTime', 'intolerances']:
        if filters.get(key):
            params[key] = filters[key]

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('results', [])
    except requests.exceptions.RequestException as exc:
        print(f"[Spoonacular] Error in advanced search: {exc}")
        return []


def get_recipe_cached(recipe_id: int):
    """
    Fetch recipe from cache if available, otherwise fetch from API and cache it.
    This saves API calls and improves performance!
    """
    from databasemodels import db, RecipeCache
    from datetime import datetime, timedelta
    
    # Check cache first (only if cached within last 7 days)
    cached = RecipeCache.query.filter_by(spoonacular_id=recipe_id).first()
    
    if cached:
        # Check if cache is still fresh (less than 7 days old)
        if datetime.utcnow() - cached.last_fetched < timedelta(days=7):
            print(f"[Cache HIT] Recipe {recipe_id} from cache")
            return cached.json_blob
        else:
            # Cache expired, delete it
            db.session.delete(cached)
            db.session.commit()
    
    # Cache miss or expired - fetch from API
    print(f"[Cache MISS] Fetching recipe {recipe_id} from API")
    recipe_data = get_recipe_details(recipe_id)
    
    if recipe_data:
        # Extract useful fields for filtering/sorting
        price = None
        if recipe_data.get('pricePerServing'):
            price = recipe_data['pricePerServing']
        
        ready_time = recipe_data.get('readyInMinutes')
        
        # Store in cache
        new_cache = RecipeCache(
            spoonacular_id=recipe_id,
            json_blob=recipe_data,
            price_per_serving=price,
            ready_in_minutes=ready_time
        )
        
        db.session.add(new_cache)
        db.session.commit()
        print(f"[Cache SAVED] Recipe {recipe_id} cached successfully")
    
    return recipe_data


# Week 9 - added suggested / autocomplete features when user is inputting ingredients in the search.]

def autocomplete_ingredients(query: str, number: int = 8):
    """
    Autocomplete ingredient suggestions as user types.
    Returns a list of ingredient names.
    """
    url = "https://api.spoonacular.com/food/ingredients/autocomplete"
    
    params = {
        "apiKey": Config.SPOONACULAR_API_KEY,
        "query": query,
        "number": number,
        "metaInformation": False,
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        results = response.json()
        # Extract just the names
        return [item['name'] for item in results]
    except requests.exceptions.RequestException as exc:
        print(f"[Spoonacular] Error in autocomplete: {exc}")
        return []