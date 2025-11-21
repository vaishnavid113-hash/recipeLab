# count_docs.py
from firebase_admin import credentials, initialize_app, firestore

cred = credentials.Certificate("serviceAccountKey.json")
initialize_app(cred)
db = firestore.client()

for coll in ['recipes','users','interactions']:
    docs = list(db.collection(coll).stream())
    print(coll, "count =", len(docs))
