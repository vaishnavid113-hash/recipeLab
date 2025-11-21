# export_firestore.py
import json
from firebase_admin import credentials, initialize_app, firestore
from pathlib import Path

SERVICE_ACCOUNT_PATH = "serviceAccountKey.json"
OUTPUT_DIR = Path("exported_json")
COLLECTIONS = ["recipes", "users", "interactions"]

def init_firestore():
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    initialize_app(cred)
    return firestore.client()

def export_collection(db, collection_name):
    docs = []
    for doc in db.collection(collection_name).stream():
        d = doc.to_dict() or {}
        # keep Firestore doc id too (useful if doc doesn't include recipe_id)
        d["_doc_id"] = doc.id
        docs.append(d)
    return docs

def main():
    db = init_firestore()
    OUTPUT_DIR.mkdir(exist_ok=True)
    for coll in COLLECTIONS:
        print(f"Exporting collection: {coll}")
        docs = export_collection(db, coll)
        out_file = OUTPUT_DIR / f"{coll}.json"
        with out_file.open("w", encoding="utf-8") as f:
            json.dump(docs, f, ensure_ascii=False, indent=2)
        print(f" -> wrote {len(docs)} documents to {out_file}")

if __name__ == "__main__":
    main()
