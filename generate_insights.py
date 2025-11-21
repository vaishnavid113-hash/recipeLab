
"""
Compute 10 analytics insights from normalized CSV output.
Writes:
 - insights_summary.json (structured)
 - insights_table.csv (row-per-insight brief)
Also prints readable output.
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np
from dateutil import parser

BASE = Path("normalized_csv")
OUT = Path("analysis_output")
OUT.mkdir(exist_ok=True)

# Load CSVs (with safe fallbacks)
def load_csv(name):
    p = BASE / name
    if not p.exists():
        raise SystemExit(f"Missing {p}. Run transform_to_csv.py first.")
    return pd.read_csv(p, dtype=str).fillna("")

df_rec = load_csv("recipes.csv")
df_ing = load_csv("ingredients.csv")
df_steps = load_csv("steps.csv")
df_int = load_csv("interactions.csv")

# Normalize types
df_rec["prep_time_minutes"] = pd.to_numeric(df_rec.get("prep_time_minutes", ""), errors="coerce")
df_rec["cook_time_minutes"] = pd.to_numeric(df_rec.get("cook_time_minutes", ""), errors="coerce")
df_rec["total_time_minutes"] = pd.to_numeric(df_rec.get("total_time_minutes", df_rec.get("total_time_minutes", "")), errors="coerce")
# ensure recipe_id column present
if "recipe_id" not in df_rec.columns:
    if "_doc_id" in df_rec.columns:
        df_rec = df_rec.rename(columns={"_doc_id": "recipe_id"})
df_rec = df_rec.set_index("recipe_id", drop=False)

# Prepare interactions: normalize type and timestamp
df_int["type"] = df_int["type"].astype(str).str.lower()
# try parse timestamp, keep original if fails
def parse_ts(x):
    try:
        return parser.parse(x)
    except Exception:
        return pd.NaT
df_int["ts_parsed"] = df_int["timestamp"].apply(parse_ts) if "timestamp" in df_int.columns else pd.NaT

# Insight 1: Most common ingredients (top 15)
df_ing["name_norm"] = df_ing["name"].astype(str).str.strip().str.lower()
top_ingredients = df_ing["name_norm"].value_counts().head(15)

# Insight 2: Average preparation time (mean, median, std)
prep_mean = float(df_rec["prep_time_minutes"].dropna().mean()) if not df_rec["prep_time_minutes"].dropna().empty else None
prep_median = float(df_rec["prep_time_minutes"].dropna().median()) if not df_rec["prep_time_minutes"].dropna().empty else None
prep_std = float(df_rec["prep_time_minutes"].dropna().std()) if not df_rec["prep_time_minutes"].dropna().empty else None

# Insight 3: Difficulty distribution
if "difficulty" in df_rec.columns:
    diff_dist = df_rec["difficulty"].astype(str).str.lower().replace("", "unknown").value_counts()
else:
    diff_dist = pd.Series(dtype=int)

# Insight 4: Correlation between prep time and likes
likes = df_int[df_int["type"]=="like"].groupby("recipe_id").size().rename("likes_count")
rec_with_likes = df_rec.join(likes, how="left").fillna({"likes_count":0})
rec_with_likes["likes_count"] = pd.to_numeric(rec_with_likes["likes_count"], errors="coerce").fillna(0)
corr_prep_likes = None
if rec_with_likes["prep_time_minutes"].notna().sum() > 2:
    corr_prep_likes = float(rec_with_likes["prep_time_minutes"].corr(rec_with_likes["likes_count"]))

# Insight 5: Most frequently viewed recipes (top 10)
views = df_int[df_int["type"]=="view"].groupby("recipe_id").size().sort_values(ascending=False)
top_viewed = views.head(10)

# Insight 6: Ingredients associated with high engagement
# Approach: compute engagement score per recipe (views + 2*likes + attempts), then aggregate by ingredient
views_count = df_int[df_int["type"]=="view"].groupby("recipe_id").size().rename("views")
likes_count = df_int[df_int["type"]=="like"].groupby("recipe_id").size().rename("likes")
attempts_count = df_int[df_int["type"]=="attempt"].groupby("recipe_id").size().rename("attempts")
eng = pd.DataFrame({"views": views_count, "likes": likes_count, "attempts": attempts_count}).fillna(0)
eng["engagement_score"] = eng["views"] + 2*eng["likes"] + 1.5*eng["attempts"]
# join ingredient -> recipe -> engagement_score
df_ing2 = df_ing.copy()
df_ing2["ing_name"] = df_ing2["name"].astype(str).str.strip().str.lower()
eng = eng.reset_index().set_index("recipe_id")
df_ing2 = df_ing2.join(eng, on="recipe_id", how="left").fillna({"engagement_score":0})
ing_eng = df_ing2.groupby("ing_name")["engagement_score"].sum().sort_values(ascending=False).head(15)

# Insight 7: Top rated recipes (average rating)
ratings = df_int[df_int["type"]=="rating"].copy()
ratings["value_num"] = pd.to_numeric(ratings["value"], errors="coerce")
avg_rating = ratings.groupby("recipe_id")["value_num"].mean().sort_values(ascending=False).head(10)

# Insight 8: Conversion rates per recipe: views -> likes, views -> attempts
conv = pd.DataFrame({
    "views": views_count,
    "likes": likes_count,
    "attempts": attempts_count
}).fillna(0)
conv["like_rate"] = (conv["likes"] / conv["views"]).replace([np.inf, -np.inf], np.nan).fillna(0)
conv["attempt_rate"] = (conv["attempts"] / conv["views"]).replace([np.inf, -np.inf], np.nan).fillna(0)
top_conv_like = conv.sort_values("like_rate", ascending=False).head(10)

# Insight 9: Engagement by difficulty (avg engagement_score per difficulty)
rec_eng = rec_with_likes.join(eng.reset_index().set_index("recipe_id")[["engagement_score"]], how="left").fillna({"engagement_score":0})
if "difficulty" in rec_eng.columns:
    rec_eng["difficulty"] = rec_eng["difficulty"].astype(str).str.lower()
    eng_by_diff = rec_eng.groupby("difficulty")["engagement_score"].mean().sort_values(ascending=False)
else:
    eng_by_diff = pd.Series(dtype=float)

# Insight 10: Time buckets effect on likes (short <15, medium 15-30, long >30)
def time_bucket(x):
    if pd.isna(x):
        return "unknown"
    try:
        x = float(x)
    except:
        return "unknown"
    if x < 15:
        return "short"
    if x <= 30:
        return "medium"
    return "long"
rec_with_likes["time_bucket"] = rec_with_likes["prep_time_minutes"].apply(time_bucket)
likes_by_bucket = rec_with_likes.groupby("time_bucket")["likes_count"].mean()

# Prepare summary dict
summary = {
    "most_common_ingredients": top_ingredients.head(15).to_dict(),
    "avg_prep_time": {"mean": prep_mean, "median": prep_median, "std": prep_std},
    "difficulty_distribution": diff_dist.to_dict(),
    "prep_likes_correlation": corr_prep_likes,
    "top_viewed_recipes": top_viewed.head(10).to_dict(),
    "ingredients_high_engagement": ing_eng.to_dict(),
    "top_rated_recipes_avg_rating": avg_rating.to_dict(),
    "top_conversion_like_rate": top_conv_like["like_rate"].head(10).to_dict(),
    "engagement_by_difficulty": eng_by_diff.to_dict(),
    "avg_likes_by_time_bucket": likes_by_bucket.to_dict()
}

# Write outputs
with open(OUT / "insights_summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

# also write human readable CSV
rows = []
rows.append({"insight":"Most common ingredients", "value": json.dumps(summary["most_common_ingredients"])})
rows.append({"insight":"Average prep time (mean/median/std)", "value": json.dumps(summary["avg_prep_time"])})
rows.append({"insight":"Difficulty distribution", "value": json.dumps(summary["difficulty_distribution"])})
rows.append({"insight":"Prep-Likes correlation (Pearson r)", "value": summary["prep_likes_correlation"]})
rows.append({"insight":"Top viewed recipes", "value": json.dumps(summary["top_viewed_recipes"])})
rows.append({"insight":"Ingredients associated with high engagement", "value": json.dumps(summary["ingredients_high_engagement"])})
rows.append({"insight":"Top rated recipes (avg rating)", "value": json.dumps(summary["top_rated_recipes_avg_rating"])})
rows.append({"insight":"Top conversion like-rate (recipes)", "value": json.dumps(summary["top_conversion_like_rate"])})
rows.append({"insight":"Engagement by difficulty", "value": json.dumps(summary["engagement_by_difficulty"])})
rows.append({"insight":"Avg likes by prep time bucket", "value": json.dumps(summary["avg_likes_by_time_bucket"])})

pd.DataFrame(rows).to_csv(OUT / "insights_table.csv", index=False)

# Print readable summary
print("Insights generated. Summary (top parts):\n")
print("1) Top ingredients (top 10):")
print(top_ingredients.head(10).to_string())
print("\n2) Average prep time (mean, median, std):", summary["avg_prep_time"])
print("\n3) Difficulty distribution:")
print(pd.Series(summary["difficulty_distribution"]).to_string())
print("\n4) Prep vs Likes correlation (Pearson r):", summary["prep_likes_correlation"])
print("\n5) Top viewed recipes (top 10):")
print(pd.Series(summary["top_viewed_recipes"]).head(10).to_string())
print("\n6) Top ingredients by engagement (top 10):")
print(pd.Series(summary["ingredients_high_engagement"]).head(10).to_string())
print("\n7) Top rated recipes (avg rating):")
print(pd.Series(summary["top_rated_recipes_avg_rating"]).to_string())
print("\n8) Example conversion rates (like_rate) - top 10 recipes by like_rate:")
print(pd.Series(summary["top_conversion_like_rate"]).to_string())
print("\n9) Engagement by difficulty (avg engagement score):")
print(pd.Series(summary["engagement_by_difficulty"]).to_string())
print("\n10) Avg likes by prep time bucket:")
print(pd.Series(summary["avg_likes_by_time_bucket"]).to_string())

print("\nWrote:", OUT / "insights_summary.json", "and", OUT / "insights_table.csv")
