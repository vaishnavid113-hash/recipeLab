import json, sys
p = "exported_json/recipes.json"
try:
    data = json.load(open(p, 'r', encoding='utf-8'))
except Exception as e:
    print("ERROR reading", p, e)
    sys.exit(1)

print("Type of top-level:", type(data))
# show first 3 recipes
if isinstance(data, dict):
    count = 0
    for k, v in data.items():
        print("--- SAMPLE ID:", k)
        print("ingredients field present?", 'ingredients' in v)
        print("ingredients value (first 300 chars):", str(v.get('ingredients'))[:300])
        print("steps present?", 'steps' in v)
        print("steps value (first 300 chars):", str(v.get('steps'))[:300])
        count += 1
        if count >= 3:
            break
else:
    for i, rec in enumerate(data):
        print("--- SAMPLE IDX:", i)
        print("id:", rec.get('recipe_id') or rec.get('_doc_id'))
        print("ingredients (first 300 chars):", str(rec.get('ingredients'))[:300])
        print("steps (first 300 chars):", str(rec.get('steps'))[:300])
        if i >= 2: break

