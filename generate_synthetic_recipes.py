# generate_synthetic_recipes.py
import random
from firebase_admin import credentials, initialize_app, firestore
import uuid

SERVICE_ACCOUNT_PATH = "serviceAccountKey.json"
cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
initialize_app(cred)
db = firestore.client()

# Small lists to combine into recipes
titles = [
    "Veg Biryani", "Masala Dosa", "Chocolate Cake", "Grilled Cheese",
    "Chana Masala", "Paneer Tikka", "Butter Chicken", "Dal Tadka",
    "Spaghetti Aglio", "Pancakes", "Miso Soup", "Tacos", "Quinoa Salad",
    "Ramen Bowl", "Falafel Wrap", "Pulav", "Vada pav", "Edli", "Puran poli","Misal pav"
]
cuisines = ["Indian", "Italian", "American", "Japanese", "Middle Eastern"]
difficulties = ["easy", "medium", "hard"]

def make_ingredients(n):
    pool = ["potato","tomato","onion","garlic","butter","cheese","flour","sugar","milk","egg","rice","peas","paneer","chili","cilantro"]
    return [{"name": random.choice(pool), "quantity": f"{random.randint(1,3)} units", "order": i+1} for i in range(n)]

def make_steps(n):
    return [{"step_number": i+1, "description": f"Step {i+1} description"} for i in range(n)]

for i, title in enumerate(titles):
    rid = title.lower().replace(" ", "-") + f"-{i+1:03d}"
    recipe = {
        "recipe_id": rid,
        "title": title,
        "description": f"A simple {title} recipe for testing.",
        "author_id": f"user_gen_{random.randint(1,5)}",
        "servings": random.choice([2,4,6]),
        "prep_time_minutes": random.randint(5,30),
        "cook_time_minutes": random.randint(10,60),
        "difficulty": random.choice(difficulties),
        "cuisine": random.choice(cuisines),
        "tags": ["synthetic", "test"],
        "ingredients": make_ingredients(random.randint(3,7)),
        "steps": make_steps(random.randint(3,6)),
        "created_at": "2025-11-17T08:00:00Z"
    }
    db.collection("recipes").document(rid).set(recipe)
    print("Inserted:", rid)

print("Done inserting synthetic recipes.")
