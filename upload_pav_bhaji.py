# upload_pav_bhaji.py
import json
from firebase_admin import credentials, initialize_app, firestore

# Change this filename if your service account key has a different name
SERVICE_ACCOUNT_PATH = "serviceAccountKey.json"

cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
initialize_app(cred)
db = firestore.client()

pav_bhaji = {
    "recipe_id": "pav-bhaji-001",
    "title": "Pav Bhaji",
    "description": "Spicy mashed vegetable curry served with buttered pav buns.",
    "author_id": "user_vaishnavi",
    "servings": 4,
    "prep_time_minutes": 15,
    "cook_time_minutes": 25,
    "difficulty": "medium",
    "cuisine": "Indian",
    "tags": ["street-food", "vegetarian", "comfort-food"],
    "ingredients": [
        {"name": "potato", "quantity": "3 medium", "order": 1},
        {"name": "cauliflower", "quantity": "1 cup chopped", "order": 2},
        {"name": "green peas", "quantity": "1/2 cup", "order": 3},
        {"name": "tomato", "quantity": "3 medium", "order": 4},
        {"name": "onion", "quantity": "2 medium", "order": 5},
        {"name": "butter", "quantity": "3 tbsp", "order": 6},
        {"name": "pav-bhaji-masala", "quantity": "2 tbsp", "order": 7},
        {"name": "turmeric", "quantity": "1/2 tsp", "order": 8},
        {"name": "red chilli powder", "quantity": "1 tsp", "order": 9},
        {"name": "salt", "quantity": "to taste", "order": 10}
    ],
    "steps": [
        {"step_number": 1, "description": "Boil potatoes, cauliflower, peas until soft."},
        {"step_number": 2, "description": "Mash vegetables roughly and keep aside."},
        {"step_number": 3, "description": "Saute onions and tomatoes, add spices and pav bhaji masala."},
        {"step_number": 4, "description": "Add mashed veg, simmer and adjust seasoning."},
        {"step_number": 5, "description": "Serve hot with buttered pav and chopped onions."}
    ],
    "created_at": "2025-11-17T08:00:00Z",
    "updated_at": "2025-11-17T08:00:00Z"
}

# Write to `recipes` collection with ID pav-bhaji-001
doc_ref = db.collection("recipes").document(pav_bhaji["recipe_id"])
doc_ref.set(pav_bhaji)
print("Inserted Pav Bhaji recipe to Firestore.")
