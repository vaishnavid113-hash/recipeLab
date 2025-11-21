# post_transform_checks.py
import pandas as pd
from pathlib import Path

P = Path("normalized_csv")
recipes = pd.read_csv(P / "recipes.csv")
ingredients = pd.read_csv(P / "ingredients.csv")
steps = pd.read_csv(P / "steps.csv")
inter = pd.read_csv(P / "interactions.csv")

print("Counts:")
print(" recipes:", len(recipes))
print(" ingredients:", len(ingredients))
print(" steps:", len(steps))
print(" interactions:", len(inter))

# Check recipes with zero ingredients
r_with_no_ing = set(recipes['recipe_id']) - set(ingredients['recipe_id'])
print("Recipes with ZERO ingredients:", len(r_with_no_ing), list(r_with_no_ing)[:5])

# Check recipes with zero steps
r_with_no_steps = set(recipes['recipe_id']) - set(steps['recipe_id'])
print("Recipes with ZERO steps:", len(r_with_no_steps), list(r_with_no_steps)[:5])

# Any interactions with missing timestamps
missing_ts = inter['timestamp'].isnull().sum() + (inter['timestamp'] == "").sum()
print("Interactions with missing/blank timestamp:", missing_ts)

# Ingredient name uniqueness sample
print("Top ingredients (sample):")
print(ingredients['name'].value_counts().head(10))
