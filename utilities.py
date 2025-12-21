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