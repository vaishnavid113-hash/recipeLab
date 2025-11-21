# seed_interactions.py
import random, datetime
from firebase_admin import credentials, initialize_app, firestore
import uuid

SERVICE_ACCOUNT_PATH = "serviceAccountKey.json"
cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
initialize_app(cred)
db = firestore.client()

# Fetch all recipe IDs currently in Firestore
recipes_docs = db.collection('recipes').stream()
recipes = [d.id for d in recipes_docs]

users_docs = db.collection('users').stream()
users = [d.id for d in users_docs]

interaction_types = ['view','like','attempt','rating']

def random_timestamp(days_back=14):
    now = datetime.datetime.utcnow()
    delta = datetime.timedelta(days=random.randint(0, days_back), hours=random.randint(0,23), minutes=random.randint(0,59))
    return (now - delta).isoformat() + "Z"

count = 50
for i in range(count):
    recipe_id = random.choice(recipes)
    user_id = random.choice(users + [None,None])  # some anonymous (None)
    itype = random.choices(interaction_types, weights=[70,15,10,5])[0]
    value = None
    if itype == 'rating':
        value = random.randint(3,5)
    doc = {
        "interaction_id": f"int-{i+1:04d}",
        "recipe_id": recipe_id,
        "user_id": user_id,
        "type": itype,
        "value": value,
        "timestamp": random_timestamp(14)
    }
    # Use auto doc id to avoid collisions:
    db.collection("interactions").add(doc)
    if (i+1) % 20 == 0:
        print("Inserted", i+1, "interactions")

print("Done inserting interactions.")
