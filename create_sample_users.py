# create_sample_users.py
from firebase_admin import credentials, initialize_app, firestore

SERVICE_ACCOUNT_PATH = "serviceAccountKey.json"
cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
initialize_app(cred)
db = firestore.client()

users = [
    {"user_id":"user_kunal","name":"Kunal Morankar","email":"kunal@example.com","signup_date":"2024-08-01T12:00:00Z","country":"India"},
    {"user_id":"user_anna","name":"Anna Smith","email":"anna@example.com","signup_date":"2024-09-10T09:00:00Z","country":"USA"},
    {"user_id":"user_li","name":"Li Wei","email":"li@example.com","signup_date":"2025-01-15T10:00:00Z","country":"China"},
    {"user_id":"user_mike","name":"Mike Johnson","email":"mike@example.com","signup_date":"2025-03-20T14:00:00Z","country":"UK"},
    {"user_id":"user_sara","name":"Sara Lee","email":"sara@example.com","signup_date":"2025-02-07T11:00:00Z","country":"Canada"},
    {"user_id":"user_rohit","name":"Rohit Sharma","email":"rohit@example.com","signup_date":"2025-04-11T12:00:00Z","country":"India"},
    {"user_id":"user_rita","name":"Rita Patel","email":"rita@example.com","signup_date":"2025-05-05T08:00:00Z","country":"India"},
    {"user_id":"user_john","name":"John Doe","email":"john@example.com","signup_date":"2025-06-15T09:00:00Z","country":"Australia"},
    {"user_id":"user_chen","name":"Chen Yu","email":"chen@example.com","signup_date":"2025-07-22T10:00:00Z","country":"China"},
    {"user_id":"user_maya","name":"Maya Gomez","email":"maya@example.com","signup_date":"2025-08-30T13:00:00Z","country":"Mexico"},
]

for u in users:
    db.collection("users").document(u["user_id"]).set(u)
    print("Created user:", u["user_id"])

print("Done creating users.")
