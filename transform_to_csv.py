# transform_to_csv.py
import json
from pathlib import Path
import pandas as pd
import uuid
from dateutil import parser

INPUT_DIR = Path("exported_json")
OUTPUT_DIR = Path("normalized_csv")
ALLOWED_DIFFICULTIES = {"easy", "medium", "hard"}
ALLOWED_INTERACTIONS = {"view", "like", "attempt", "rating"}

def load_json(filename):
    p = INPUT_DIR / filename
    if not p.exists():
        raise FileNotFoundError(f"{p} not found. Run export_firestore.py first.")
    return json.load(open(p, "r", encoding="utf-8"))

def safe_int(x, default=None):
    try:
        if x is None:
            return default
        return int(x)
    except Exception:
        return default

def safe_str(x, default=""):
    if x is None:
        return default
    return str(x)

def normalize_recipes(recipes_raw):
    rows = []
    ingredients_rows = []
    steps_rows = []

    for doc in recipes_raw:
        # prefer explicit recipe_id field; else use Firestore doc id
        recipe_id = doc.get("recipe_id") or doc.get("_doc_id")
        title = safe_str(doc.get("title"))
        description = safe_str(doc.get("description", ""))
        author_id = safe_str(doc.get("author_id", ""))
        servings = safe_int(doc.get("servings"), default=None)
        prep = safe_int(doc.get("prep_time_minutes"), default=0)
        cook = safe_int(doc.get("cook_time_minutes"), default=0)
        total = prep + cook
        difficulty = (doc.get("difficulty") or "").lower()
        if difficulty not in ALLOWED_DIFFICULTIES:
            # if missing or invalid, set to 'medium' as default
            difficulty = "medium"
        cuisine = safe_str(doc.get("cuisine", ""))
        tags = doc.get("tags") or []
        if isinstance(tags, list):
            tags_join = "|".join([safe_str(t) for t in tags])
        else:
            tags_join = safe_str(tags)

        rows.append({
            "recipe_id": recipe_id,
            "title": title,
            "description": description,
            "author_id": author_id,
            "servings": servings,
            "prep_time_minutes": prep,
            "cook_time_minutes": cook,
            "total_time_minutes": total,
            "difficulty": difficulty,
            "cuisine": cuisine,
            "tags": tags_join,
            "created_at": safe_str(doc.get("created_at", "")),
            "updated_at": safe_str(doc.get("updated_at", ""))
        })

        # Ingredients
        ingredients = doc.get("ingredients") or []
        if isinstance(ingredients, dict):
            # handle case where ingredients stored as map rather than list
            ingredients = list(ingredients.values())

        for ing in ingredients:
            # each ing should be dict with name, quantity, order (order optional)
            name = safe_str(ing.get("name") if isinstance(ing, dict) else ing)
            quantity = safe_str(ing.get("quantity") if isinstance(ing, dict) else "")
            order = safe_int(ing.get("order") if isinstance(ing, dict) else None, default=None)
            ingredient_id = str(uuid.uuid4())
            ingredients_rows.append({
                "recipe_id": recipe_id,
                "ingredient_id": ingredient_id,
                "name": name.strip().lower(),
                "quantity": quantity.strip(),
                "order": order
            })

        # Steps
        steps = doc.get("steps") or []
        if isinstance(steps, dict):
            steps = list(steps.values())
        for s in steps:
            step_number = safe_int(s.get("step_number") if isinstance(s, dict) else None, default=None)
            description = safe_str(s.get("description") if isinstance(s, dict) else s)
            # If step_number missing, we will assign later based on order
            steps_rows.append({
                "recipe_id": recipe_id,
                "step_number": step_number,
                "description": description.strip()
            })

    # Post-process: set missing step_number sequentially per recipe
    df_steps = pd.DataFrame(steps_rows)
    if not df_steps.empty:
        df_steps["step_number"] = (
    df_steps.groupby("recipe_id").cumcount() + 1
)
        # for any still-NaN step_numbers, assign by appearance order
        def assign_seq(sub):
            if sub["step_number"].isnull().any():
                sub = sub.reset_index(drop=True)
                seqs = list(range(1, len(sub) + 1))
                sub["step_number"] = sub["step_number"].fillna(pd.Series(seqs))
            return sub
        df_steps = df_steps.groupby("recipe_id", group_keys=False).apply(assign_seq)
    else:
        df_steps = pd.DataFrame(columns=["recipe_id", "step_number", "description"])

    df_recipes = pd.DataFrame(rows)
    df_ingredients = pd.DataFrame(ingredients_rows)

    return df_recipes, df_ingredients, df_steps

def normalize_interactions(inter_raw):
    rows = []
    for it in inter_raw:
        interaction_id = it.get("interaction_id") or it.get("_doc_id") or str(uuid.uuid4())
        recipe_id = it.get("recipe_id") or it.get("recipe") or it.get("recipe_id_from_doc")
        user_id = it.get("user_id")  # allow None (anonymous)
        itype = (it.get("type") or "").lower()
        if itype not in ALLOWED_INTERACTIONS:
            # if unknown type, fallback to 'view'
            itype = "view"
        value = it.get("value")
        timestamp = it.get("timestamp") or it.get("created_at") or ""
        # try to normalize timestamp to ISO8601
        try:
            timestamp_normal = parser.isoparse(timestamp).isoformat()
        except Exception:
            timestamp_normal = ""
        rows.append({
            "interaction_id": interaction_id,
            "recipe_id": recipe_id,
            "user_id": user_id,
            "type": itype,
            "value": value,
            "timestamp": timestamp_normal
        })
    df = pd.DataFrame(rows)
    return df

def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    recipes_raw = load_json("recipes.json")
    inter_raw = load_json("interactions.json")

    print(f"Loaded {len(recipes_raw)} recipes and {len(inter_raw)} interactions")

    df_recipes, df_ingredients, df_steps = normalize_recipes(recipes_raw)
    df_interactions = normalize_interactions(inter_raw)

    # Optional cleaning steps:
    # - Drop recipes without recipe_id
    df_recipes = df_recipes[df_recipes["recipe_id"].notnull()]

    # - Ensure interactions refer to existing recipes (inner join)
    valid_recipe_ids = set(df_recipes["recipe_id"].unique())
    before = len(df_interactions)
    df_interactions = df_interactions[df_interactions["recipe_id"].isin(valid_recipe_ids)]
    after = len(df_interactions)
    print(f"Filtered interactions: {before} -> {after} (only those with recipe present)")

    # Write CSVs
    df_recipes.to_csv(OUTPUT_DIR / "recipes.csv", index=False)
    df_ingredients.to_csv(OUTPUT_DIR / "ingredients.csv", index=False)
    df_steps.to_csv(OUTPUT_DIR / "steps.csv", index=False)
    df_interactions.to_csv(OUTPUT_DIR / "interactions.csv", index=False)

    print("Wrote CSVs to normalized_csv/")

if __name__ == "__main__":
    main()
