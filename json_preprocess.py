# preprocess_cities.py
import json
import re

INPUT_FILE = "city_list.json"
OUTPUT_FILE = "locations.txt"

valid_name = re.compile(r"[A-Za-zÀ-ÿ]")  # allow accented letters

unique = set()

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    cities = json.load(f)

for city in cities:
    name = city.get("name", "").strip()
    country = city.get("country", "").strip()

    # skip invalid entries
    if not name or not country:
        continue
    if not valid_name.search(name):  # must contain letters
        continue
    if len(name) < 2:
        continue

    display = f"{name},{country}"
    unique.add(display)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    for city in sorted(unique):
        f.write(city + "\n")

print(f"Cleaned locations.txt created with {len(unique)} entries")
