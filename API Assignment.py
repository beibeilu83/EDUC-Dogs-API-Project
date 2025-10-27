

from typing import Dict, Any, List, Optional
import requests
import json


# -------- Step 0. Shared HTTP configuration --------
HEADERS = {"User-Agent": "PetCal-Web/1.3 (GET-only)"}
TIMEOUT = 12.0


# -------- Step 1. Small helper to GET+parse JSON --------
def fetch_json(url: str) -> Optional[dict]:
    """
    Issue a GET request and parse JSON.
    Returns None on any network/parse error so the caller can skip gracefully.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


# -------- Step 2. GET dog categories from dog.ceo --------
def get_dog_categories() -> List[str]:
    """
    Fetch the full breeds list from dog.ceo and flatten to "category" strings.
    Example: "retriever-golden", "bulldog-english", or just "akita".
    """
    data = fetch_json("https://dog.ceo/api/breeds/list/all")
    if not data or "message" not in data:
        return []

    breeds = data["message"]  # {breed: [subbreeds]}
    categories: List[str] = []
    for breed, subs in breeds.items():
        if subs:
            for s in subs:
                categories.append(f"{breed}-{s}")
        else:
            categories.append(breed)
    return sorted(categories)


# -------- Step 3. GET a large batch of general dog facts, then filter --------
def get_food_related_facts() -> Dict[str, List[str]]:
    """
    Pull a large batch of random facts from Kinduff (supports ?number=...),
    then filter them into three buckets by simple keyword matching:

      - good_foods: likely "okay" items (e.g., chicken, rice, carrots)
      - avoid_foods: toxic/unsafe items (e.g., chocolate, grapes, onions)
      - calorie_facts: anything mentioning calories/energy/kcal (informational)

    NOTE:
    - These facts are unstructured trivia, so we do best-effort keyword filtering.
    - If nothing matches, lists remain empty; callers can skip.
    """
    results = {"good_foods": [], "avoid_foods": [], "calorie_facts": []}

    data = fetch_json("https://dog-api.kinduff.com/api/facts?number=200")
    if not data or "facts" not in data or not data["facts"]:
        return results

    # Deduplicate, keep only strings
    facts = []
    seen = set()
    for f in data["facts"]:
        if isinstance(f, str):
            s = f.strip()
            if s and s not in seen:
                facts.append(s)
                seen.add(s)

    # Keyword sets (broad on purpose; adjust as needed)
    avoid_terms = [
        "chocolate", "cocoa", "grape", "grapes", "raisin", "raisins",
        "onion", "onions", "garlic", "xylitol", "alcohol", "beer", "wine",
        "coffee", "caffeine", "tea", "macadamia", "nutmeg", "yeast dough",
        "raw dough", "raw bread", "avocado"
    ]
    good_terms = [
        "chicken", "turkey", "beef", "lamb", "fish", "salmon", "tuna",
        "rice", "brown rice", "oats", "oatmeal", "pumpkin", "carrot",
        "carrots", "apple", "apples", "blueberries", "peanut butter",
        "sweet potato", "yogurt"
    ]
    calorie_terms = ["calorie", "calories", "kcal", "energy", "metabolic"]

    def matches_any(text: str, terms: List[str]) -> bool:
        t = text.lower()
        return any(term in t for term in terms)

    # Classify each fact into ONE bucket by priority: calorie -> avoid -> good
    for fact in facts:
        low = fact.lower()
        if matches_any(low, calorie_terms):
            results["calorie_facts"].append(fact)
        elif matches_any(low, avoid_terms):
            results["avoid_foods"].append(fact)
        elif matches_any(low, good_terms):
            results["good_foods"].append(fact)

    return results


# -------- Step 4. Aggregate only the requested outputs --------
def gather_dog_info() -> Dict[str, Any]:
    """
    Build the final result dict containing only the available keys:
      - "dog_categories"
      - "good_foods"
      - "avoid_foods"
      - "calorie_facts"
    We intentionally do NOT include "calorie_needs_by_category"
    because these APIs don't provide that data.
    """
    info: Dict[str, Any] = {}

    # 4.1 Dog categories (breeds) — structured and reliable
    categories = get_dog_categories()
    if categories:
        info["dog_categories"] = categories

    # 4.2 Food-related items — best effort from general facts
    food = get_food_related_facts()
    if food.get("good_foods"):
        info["good_foods"] = food["good_foods"]
    if food.get("avoid_foods"):
        info["avoid_foods"] = food["avoid_foods"]
    if food.get("calorie_facts"):
        info["calorie_facts"] = food["calorie_facts"]

    # 4.3 Calories needed per category — not available -> skipped automatically
    # (If you later add a vetted nutrition dataset, compute/category-map here.)

    return info


# -------- Step 5. Simple CLI output for quick verification --------
def _print_sample(result: Dict[str, Any], key: str, n: int = 5) -> None:
    if key not in result:
        return
    print(f"\n=== {key.upper()} (sample) ===")
    items = result[key]
    if isinstance(items, list):
        for v in items[:n]:
            print("-", v)
    else:
        print(items)

if __name__ == "__main__":
    info = gather_dog_info()
    print("Fetched keys:", list(info.keys()) or "(none)")
    _print_sample(info, "dog_categories", n=10)
    _print_sample(info, "good_foods", n=5)
    _print_sample(info, "avoid_foods", n=5)
    _print_sample(info, "calorie_facts", n=5)


