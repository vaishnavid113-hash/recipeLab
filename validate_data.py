# validate_data.py
"""
Validator for Firestore exports (JSON) or normalized CSVs.
Produces:
 - validation_report.json  (summary counts + examples)
 - invalid_recipes.csv
 - invalid_interactions.csv
 - invalid_users.csv
"""

import json
import re
from pathlib import Path
from dateutil import parser
import pandas as pd

# CONFIG
EXPORT_JSON_DIR = Path("exported_json")
NORMALIZED_DIR = Path("normalized_csv")
OUTPUT_DIR = Path("validation_output")
OUTPUT_DIR.mkdir(exist_ok=True)

ALLOWED_DIFFICULTIES = {"easy", "medium", "hard"}
ALLOWED_INTERACTIONS = {"view", "like", "attempt", "rating"}

EMAIL_RE = re.compile(r"^[^@]+@[^@]+\.[^@]+$")

# Helpers
def load_json_file(p: Path):
    if not p.exists():
        return []
    try:
        return json.load(open(p, "r", encoding="utf-8"))
    except Exception as e:
        print(f"ERROR reading {p}: {e}")
        return []

def safe_get_id(doc):
    # Accept recipe_id or _doc_id
    return doc.get("recipe_id") or doc.get("interaction_id") or doc.get("user_id") or doc.get("_doc_id") or None

def is_parseable_timestamp(ts):
    if not ts:
        return False
    try:
        parser.isoparse(ts)
        return True
    except Exception:
        try:
            parser.parse(ts)
            return True
        except Exception:
            return False

# Validation functions
def validate_recipe(doc):
    """
    Returns (is_valid:bool, reasons:list)
    """
    reasons = []
    recipe_id = doc.get("recipe_id") or doc.get("_doc_id")
    if not recipe_id:
        reasons.append("missing recipe_id/_doc_id")
    if not doc.get("title"):
        reasons.append("missing title")
    # times
    def check_nonneg(name):
        val = doc.get(name)
        if val is None:
            reasons.append(f"missing {name}")
            return
        try:
            iv = int(val)
            if iv < 0:
                reasons.append(f"{name} negative")
        except Exception:
            reasons.append(f"{name} not integer")
    check_nonneg("prep_time_minutes")
    check_nonneg("cook_time_minutes")
    # difficulty
    diff = (doc.get("difficulty") or "").lower()
    if diff and diff not in ALLOWED_DIFFICULTIES:
        reasons.append("invalid difficulty")
    if not diff:
        reasons.append("missing difficulty")
    # ingredients
    ings = doc.get("ingredients")
    if not ings:
        reasons.append("empty ingredients")
    else:
        # could be dict or list
        if isinstance(ings, dict):
            ings_list = list(ings.values())
        else:
            ings_list = ings
        if len(ings_list) == 0:
            reasons.append("empty ingredients")
        else:
            for idx, ing in enumerate(ings_list, start=1):
                # if ingredient is a simple string, allow but flag missing quantity
                if isinstance(ing, dict):
                    if not (ing.get("name") and str(ing.get("name")).strip()):
                        reasons.append(f"ingredient_{idx}: missing name")
                else:
                    # string or other; ensure it's not empty
                    if not str(ing).strip():
                        reasons.append(f"ingredient_{idx}: empty entry")
    # steps
    steps = doc.get("steps")
    if not steps:
        reasons.append("empty steps")
    else:
        if isinstance(steps, dict):
            steps_list = list(steps.values())
        else:
            steps_list = steps
        if len(steps_list) == 0:
            reasons.append("empty steps")
        else:
            for idx, st in enumerate(steps_list, start=1):
                if isinstance(st, dict):
                    if not (st.get("description") and str(st.get("description")).strip()):
                        reasons.append(f"step_{idx}: missing description")
                else:
                    if not str(st).strip():
                        reasons.append(f"step_{idx}: empty description")
    valid = len(reasons) == 0
    return valid, reasons

def validate_interaction(doc, known_recipe_ids=None):
    reasons = []
    iid = doc.get("interaction_id") or doc.get("_doc_id")
    if not iid:
        reasons.append("missing interaction_id/_doc_id")
    recipe_id = doc.get("recipe_id")
    if not recipe_id:
        reasons.append("missing recipe_id")
    elif known_recipe_ids is not None and recipe_id not in known_recipe_ids:
        reasons.append("recipe_id not found in recipes")
    typ = (doc.get("type") or "").lower()
    if not typ:
        reasons.append("missing type")
    elif typ not in ALLOWED_INTERACTIONS:
        reasons.append("invalid type")
    ts = doc.get("timestamp") or doc.get("created_at")
    if not is_parseable_timestamp(ts):
        reasons.append("invalid/missing timestamp")
    if typ == "rating":
        v = doc.get("value")
        try:
            vi = int(v)
            if vi < 1 or vi > 5:
                reasons.append("rating value out of range")
        except Exception:
            reasons.append("rating value not int")
    return (len(reasons) == 0), reasons

def validate_user(doc):
    reasons = []
    uid = doc.get("user_id") or doc.get("_doc_id")
    if not uid:
        reasons.append("missing user_id/_doc_id")
    email = doc.get("email")
    if email:
        if not EMAIL_RE.match(email):
            reasons.append("invalid email format")
    return (len(reasons) == 0), reasons

# Main flow: prefer normalized CSVs if present, else JSON exports
def main():
    report = {
        "recipes": {"total": 0, "valid": 0, "invalid": 0, "invalid_examples": []},
        "interactions": {"total": 0, "valid": 0, "invalid": 0, "invalid_examples": []},
        "users": {"total": 0, "valid": 0, "invalid": 0, "invalid_examples": []}
    }

    # Load recipes
    recipes_raw = []
    if (NORMALIZED_DIR / "recipes.csv").exists():
        df = pd.read_csv(NORMALIZED_DIR / "recipes.csv", dtype=str).fillna("")
        # convert rows to dicts with minimal fields expected by validator
        for _, r in df.iterrows():
            # convert tags pipe back to list
            tags = r.get("tags", "")
            tags_list = tags.split("|") if isinstance(tags, str) and tags else []
            recipes_raw.append({
                "recipe_id": r.get("recipe_id") or r.get("_doc_id"),
                "title": r.get("title"),
                "prep_time_minutes": r.get("prep_time_minutes"),
                "cook_time_minutes": r.get("cook_time_minutes"),
                "difficulty": r.get("difficulty"),
                "ingredients": [],  # we can't easily reconstruct from CSV here
                "steps": []
            })
    else:
        recipes_raw = load_json_file(EXPORT_JSON_DIR / "recipes.json")

    # Validate recipes
    recipe_ids = set()
    invalid_recipes = []
    for doc in recipes_raw:
        report["recipes"]["total"] += 1
        valid, reasons = validate_recipe(doc)
        rid = doc.get("recipe_id") or doc.get("_doc_id")
        if rid:
            recipe_ids.add(rid)
        if valid:
            report["recipes"]["valid"] += 1
        else:
            report["recipes"]["invalid"] += 1
            example = {"recipe_id": rid, "reasons": reasons, "raw": doc}
            report["recipes"]["invalid_examples"].append({"recipe_id": rid, "reasons": reasons})
            # For CSV of invalids, flatten minimal columns
            flat = {"recipe_id": rid, "title": doc.get("title"), "reasons": "; ".join(reasons)}
            invalid_recipes.append(flat)

    # Save invalid recipes
    if invalid_recipes:
        pd.DataFrame(invalid_recipes).to_csv(OUTPUT_DIR / "invalid_recipes.csv", index=False)

    # Load interactions
    if (NORMALIZED_DIR / "interactions.csv").exists():
        df_int = pd.read_csv(NORMALIZED_DIR / "interactions.csv", dtype=str).fillna("")
        interactions_raw = df_int.to_dict(orient="records")
    else:
        interactions_raw = load_json_file(EXPORT_JSON_DIR / "interactions.json")

    invalid_interactions = []
    for doc in interactions_raw:
        report["interactions"]["total"] += 1
        valid, reasons = validate_interaction(doc, known_recipe_ids=recipe_ids)
        iid = doc.get("interaction_id") or doc.get("_doc_id")
        if valid:
            report["interactions"]["valid"] += 1
        else:
            report["interactions"]["invalid"] += 1
            report["interactions"]["invalid_examples"].append({"interaction_id": iid, "reasons": reasons})
            invalid_interactions.append({
                "interaction_id": iid,
                "recipe_id": doc.get("recipe_id"),
                "type": doc.get("type"),
                "timestamp": doc.get("timestamp") or doc.get("created_at"),
                "reasons": "; ".join(reasons)
            })
    if invalid_interactions:
        pd.DataFrame(invalid_interactions).to_csv(OUTPUT_DIR / "invalid_interactions.csv", index=False)

    # Load users
    if (NORMALIZED_DIR / "users.csv").exists():
        df_users = pd.read_csv(NORMALIZED_DIR / "users.csv", dtype=str).fillna("")
        users_raw = df_users.to_dict(orient="records")
    else:
        users_raw = load_json_file(EXPORT_JSON_DIR / "users.json")

    invalid_users = []
    for doc in users_raw:
        report["users"]["total"] += 1
        valid, reasons = validate_user(doc)
        uid = doc.get("user_id") or doc.get("_doc_id")
        if valid:
            report["users"]["valid"] += 1
        else:
            report["users"]["invalid"] += 1
            report["users"]["invalid_examples"].append({"user_id": uid, "reasons": reasons})
            invalid_users.append({"user_id": uid, "email": doc.get("email"), "reasons": "; ".join(reasons)})

    if invalid_users:
        pd.DataFrame(invalid_users).to_csv(OUTPUT_DIR / "invalid_users.csv", index=False)

    # Write full JSON report
    with open(OUTPUT_DIR / "validation_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Print quick summary
    print("Validation complete. Summary:")
    print(json.dumps({
        "recipes": report["recipes"],
        "interactions": report["interactions"],
        "users": report["users"]
    }, indent=2))

    print(f"\nOutputs written to: {OUTPUT_DIR.resolve()}")
    if (OUTPUT_DIR / "invalid_recipes.csv").exists():
        print(" - invalid_recipes.csv")
    if (OUTPUT_DIR / "invalid_interactions.csv").exists():
        print(" - invalid_interactions.csv")
    if (OUTPUT_DIR / "invalid_users.csv").exists():
        print(" - invalid_users.csv")
    print(" - validation_report.json")

if __name__ == "__main__":
    main()
