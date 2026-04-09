import math
import random
from typing import Any, Dict, List, Tuple

VALID_TASTES = frozenset({"sweet", "spicy", "umami", "fresh"})
VALID_TIME_FIT = frozenset({"lunch", "dinner", "snack"})

FLAVOR_TO_TASTE: Dict[str, str] = {
    "spicy": "spicy",
    "sweet": "sweet",
    "savory": "umami",
}

_SOCIAL_OCCASION_SLOTS: Dict[str, frozenset] = {
    "lunch": frozenset({"lunch"}),
    "dinner": frozenset({"dinner"}),
    "snack": frozenset({"snack"}),
    "coffee_break": frozenset({"snack"}),
    "quick_snack": frozenset({"snack"}),
    "business_lunch": frozenset({"lunch"}),
    "full_meal": frozenset({"lunch", "dinner"}),
    "meeting_place": frozenset({"lunch", "snack"}),
}

DEFAULT_WEIGHTS: Dict[str, float] = {
    "price_base_penalty": 2.0,
    "price_sensitivity_multiplier": 3.5,
    "relative_price_coef": 1.2,
    "utility_scale": 3.5,
    "temperature": 1.7,
    "max_price_impact": 0.5,
    "budget_bonus": 0.25,
    "protein_coef": 0.8,
    "calories_coef": -0.25,
    "spicy_bonus": 0.35,
    "mild_vs_spicy_penalty": -0.15,
    "healthy_bonus": 0.55,
    "low_sugar_coef": -0.45,
    "high_protein_bonus": 0.65,
    "vegetarian_bonus": 0.8,
    "vegetarian_meat_penalty": -1.4,
    "full_meal_main_bonus": 0.3,
    "snack_small_item_bonus": 0.45,
    "family_comfort_bonus": 0.25,
    "preferred_healthy_bonus": 0.3,
    "preferred_american_bonus": 0.2,
    "novelty_bonus": 0.15,
    "substitution_overlap_coef": -0.12,
    "noise_sigma": 0.18,
    "drink_prob_base": 0.45,
    "drink_prob_digital_coef": 0.25,
    "extra_prob_base": 0.25,
    "extra_prob_orders_coef": 0.1,
    "taste_match_weight": 0.45,
    "time_fit_bonus": 0.28,
    "satiety_weight": 0.12,
}


def softmax(values: List[float], temperature: float = 1.0) -> List[float]:
    if not values:
        return []
    t = max(temperature, 1e-6)
    scaled = [v / t for v in values]
    m = max(scaled)
    exps = [math.exp(v - m) for v in scaled]
    s = sum(exps)
    if s <= 0:
        return [1.0 / len(values)] * len(values)
    return [v / s for v in exps]


def sample_index(probabilities: List[float], rng: random.Random) -> int:
    r = rng.random()
    cumulative = 0.0
    for i, p in enumerate(probabilities):
        cumulative += p
        if r <= cumulative:
            return i
    return len(probabilities) - 1


def _safe_num(value: Any, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _level_to_num(value: str, mapping: Dict[str, float], default: float = 0.0) -> float:
    if not isinstance(value, str):
        return default
    return mapping.get(value, default)


def _normalized_taste_list(raw: Any) -> List[str]:
    if not isinstance(raw, list):
        return []
    out: List[str] = []
    for x in raw:
        if isinstance(x, str) and x in VALID_TASTES:
            out.append(x)
    return out


def _user_taste_preferences(user: Dict[str, Any]) -> frozenset:
    fp = user.get("food_preferences") or {}
    explicit = fp.get("taste_preferences")
    acc: set = set()
    if isinstance(explicit, list):
        acc.update(t for t in explicit if isinstance(t, str) and t in VALID_TASTES)
    if acc:
        return frozenset(acc)
    flavors = fp.get("flavor_preferences")
    if isinstance(flavors, list):
        for f in flavors:
            if isinstance(f, str) and f in FLAVOR_TO_TASTE:
                acc.add(FLAVOR_TO_TASTE[f])
    return frozenset(acc)


def taste_match(user: Dict[str, Any], item: Dict[str, Any]) -> float:
    """Anteil der Nutzer-Taste-Präferenzen, die das Gericht trifft (0..1)."""
    item_tastes = set(_normalized_taste_list(item.get("taste")))
    if not item_tastes:
        return 0.0
    user_tastes = _user_taste_preferences(user)
    if not user_tastes:
        return 0.0
    inter = user_tastes & item_tastes
    return len(inter) / float(len(user_tastes))


def _user_occasion_slots(user: Dict[str, Any]) -> frozenset:
    top = user.get("occasion")
    if isinstance(top, str) and top in VALID_TIME_FIT:
        return frozenset({top})
    sc = user.get("social_context") or {}
    occ = sc.get("occasion", "")
    if isinstance(occ, str) and occ in _SOCIAL_OCCASION_SLOTS:
        return _SOCIAL_OCCASION_SLOTS[occ]
    return frozenset()


def _normalized_time_fit(raw: Any) -> frozenset:
    if not isinstance(raw, list):
        return frozenset()
    return frozenset(x for x in raw if isinstance(x, str) and x in VALID_TIME_FIT)


def satiety_score(item: Dict[str, Any]) -> float:
    cals = _safe_num(item.get("calories"), 0.0)
    price = max(_safe_num(item.get("price_rub"), 0.0), 1.0)
    return cals / price


def _build_user_profile(user: Dict[str, Any]) -> Dict[str, float]:
    price_map = {"low": 0.2, "medium": 0.5, "medium_to_high": 0.75, "high": 1.0}
    openness_map = {"low": 0.2, "medium": 0.5, "high": 0.9}
    digital_map = {"low": 0.2, "medium": 0.5, "high": 0.9}

    psych = user.get("psychographics", {})
    meal = user.get("meal_behavior", {})
    channel = user.get("channel_preferences", {})

    return {
        "budget_rub": _safe_num(user.get("monthly_income_rub"), 60000.0) / 20.0,
        "avg_check_rub": _safe_num(meal.get("avg_order_check_rub"), 700.0),
        "price_sensitivity": _level_to_num(psych.get("price_sensitivity", "medium"), price_map, 0.5),
        "openness": _level_to_num(meal.get("new_menu_openness", "medium"), openness_map, 0.5),
        "digital": _level_to_num(channel.get("digital_intensity", "medium"), digital_map, 0.5),
        "orders_per_week": _safe_num(meal.get("orders_per_week"), 3.0),
    }


def _item_utility(
    user: Dict[str, Any],
    item: Dict[str, Any],
    profile: Dict[str, float],
    avg_menu_price: float,
    picked_tags: set,
    rng: random.Random,
    weights: Dict[str, float],
) -> float:
    tags = set(item.get("tags", []))
    category = item.get("category", "")

    price = _safe_num(item.get("price_rub"), 0.0)
    calories = _safe_num(item.get("calories"), 0.0)
    protein = _safe_num(item.get("protein_g"), 0.0)
    sugar = _safe_num(item.get("sugar_g"), 0.0)

    diet = user.get("diet_profile", "")
    preferred = set(user.get("food_preferences", {}).get("preferred_cuisines", []))
    flavor_prefs = set(user.get("food_preferences", {}).get("flavor_preferences", []))
    occasion = user.get("social_context", {}).get("occasion", "")
    company = user.get("social_context", {}).get("company", "")

    utility = 0.0

    # Price utility: stronger penalty for price-sensitive users.
    over_avg_check_raw = max(0.0, price - profile["avg_check_rub"]) / max(profile["avg_check_rub"], 1.0)
    over_avg_check = min(over_avg_check_raw, weights["max_price_impact"])
    utility -= (
        weights["price_base_penalty"] + weights["price_sensitivity_multiplier"] * profile["price_sensitivity"]
    ) * over_avg_check
    if price <= profile["budget_rub"] * 0.55:
        utility += weights["budget_bonus"]
    relative_price = price / max(avg_menu_price, 1.0)
    utility -= relative_price * weights["relative_price_coef"]

    # Basic nutrition utility.
    utility += min(protein / 45.0, 1.2) * weights["protein_coef"]
    utility += min(calories / 1200.0, 1.0) * weights["calories_coef"]

    utility += weights["satiety_weight"] * satiety_score(item)
    utility += weights["taste_match_weight"] * taste_match(user, item)

    user_slots = _user_occasion_slots(user)
    item_slots = _normalized_time_fit(item.get("time_fit"))
    if user_slots and item_slots and (user_slots & item_slots):
        utility += weights["time_fit_bonus"]

    # Context and preferences.
    if "spicy" in flavor_prefs and "spicy" in tags:
        utility += weights["spicy_bonus"]
    if "mild" in flavor_prefs and "spicy" in tags:
        utility += weights["mild_vs_spicy_penalty"]

    if diet in {"healthy_lifestyle", "weight_control"}:
        if "healthy" in tags or category == "salad":
            utility += weights["healthy_bonus"]
        utility += min(sugar / 20.0, 1.0) * weights["low_sugar_coef"]
    if diet in {"high_protein", "muscle_gain"} and ("high_protein" in tags or protein >= 30):
        utility += weights["high_protein_bonus"]
    if diet in {"vegetarian", "plant_based"} and ("vegetarian" in tags or "plant_based" in tags):
        utility += weights["vegetarian_bonus"]
    if diet in {"vegetarian", "plant_based"} and (
        "chicken" in tags or "steak" in tags or "fish" in tags or "salmon" in tags
    ):
        utility += weights["vegetarian_meat_penalty"]

    # Occasion / company.
    if occasion in {"full_meal", "lunch", "dinner"} and category in {"protein_plate", "bowl", "salad"}:
        utility += weights["full_meal_main_bonus"]
    if occasion in {"snack", "coffee_break"} and category in {"dessert", "side", "drink"}:
        utility += weights["snack_small_item_bonus"]
    if company in {"family_dinner", "friends"} and "comfort" in tags:
        utility += weights["family_comfort_bonus"]

    # Preferred cuisines are broad; map softly through tags.
    if "healthy" in preferred and "healthy" in tags:
        utility += weights["preferred_healthy_bonus"]
    if "american" in preferred and ("bbq" in tags or "burger" in tags):
        utility += weights["preferred_american_bonus"]

    # Novelty effect.
    if profile["openness"] >= 0.7 and ("premium" in tags or "functional" in tags):
        utility += weights["novelty_bonus"]

    # Substitution penalty: discourage near-duplicate tags in bundle.
    overlap = len(tags.intersection(picked_tags))
    utility += weights["substitution_overlap_coef"] * overlap

    # Stochastic component (Gumbel-like approximation via Gaussian noise for simplicity).
    utility += rng.gauss(0.0, weights["noise_sigma"])
    return utility * weights["utility_scale"]


def choose_bundle(
    user: Dict[str, Any],
    menu_items: List[Dict[str, Any]],
    rng: random.Random,
    weights: Dict[str, float],
) -> List[int]:
    profile = _build_user_profile(user)
    prices = [_safe_num(it.get("price_rub"), 0.0) for it in menu_items]
    avg_menu_price = sum(prices) / len(prices) if prices else 1.0
    items_by_idx = {i: it for i, it in enumerate(menu_items)}

    # Stage 1: choose a main dish.
    main_candidates = [i for i, it in items_by_idx.items() if it.get("category") in {"protein_plate", "bowl", "salad"}]
    if not main_candidates:
        main_candidates = list(items_by_idx.keys())

    picked: List[int] = []
    picked_tags: set = set()

    main_utils = [
        _item_utility(user, items_by_idx[i], profile, avg_menu_price, picked_tags, rng, weights)
        for i in main_candidates
    ]
    main_probs = softmax(main_utils, temperature=weights["temperature"])
    chosen_main = main_candidates[sample_index(main_probs, rng)]
    picked.append(chosen_main)
    picked_tags.update(items_by_idx[chosen_main].get("tags", []))

    # Stage 2: optional drink.
    drink_prob = weights["drink_prob_base"] + weights["drink_prob_digital_coef"] * profile["digital"]
    if rng.random() < min(max(drink_prob, 0.05), 0.9):
        drink_candidates = [i for i, it in items_by_idx.items() if it.get("category") == "drink"]
        if drink_candidates:
            drink_utils = [
                _item_utility(user, items_by_idx[i], profile, avg_menu_price, picked_tags, rng, weights)
                for i in drink_candidates
            ]
            drink_probs = softmax(drink_utils, temperature=weights["temperature"])
            chosen_drink = drink_candidates[sample_index(drink_probs, rng)]
            picked.append(chosen_drink)
            picked_tags.update(items_by_idx[chosen_drink].get("tags", []))

    # Stage 3: optional side or dessert.
    side_prob = weights["extra_prob_base"] + weights["extra_prob_orders_coef"] * min(
        profile["orders_per_week"] / 7.0, 1.0
    )
    if rng.random() < min(max(side_prob, 0.05), 0.7):
        extra_candidates = [i for i, it in items_by_idx.items() if it.get("category") in {"side", "dessert"}]
        if extra_candidates:
            extra_utils = [
                _item_utility(user, items_by_idx[i], profile, avg_menu_price, picked_tags, rng, weights)
                for i in extra_candidates
            ]
            extra_probs = softmax(extra_utils, temperature=weights["temperature"])
            chosen_extra = extra_candidates[sample_index(extra_probs, rng)]
            picked.append(chosen_extra)

    # Return unique indices in order.
    seen = set()
    unique_picked = []
    for idx in picked:
        if idx not in seen:
            seen.add(idx)
            unique_picked.append(idx)
    return unique_picked


def evaluate_orders(
    users: List[Dict[str, Any]],
    menu_items: List[Dict[str, Any]],
    seed: int = 42,
    weights: Dict[str, float] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    rng = random.Random(seed)
    active_weights = dict(DEFAULT_WEIGHTS)
    if weights:
        active_weights.update(weights)
    orders: List[Dict[str, Any]] = []

    revenue = 0.0
    total_items = 0
    item_counts: Dict[str, int] = {}

    for user_idx, user in enumerate(users):
        chosen_internal_idx = choose_bundle(user, menu_items, rng, active_weights)
        selected_items = [menu_items[i] for i in chosen_internal_idx]

        total_rub = sum(_safe_num(it.get("price_rub"), 0.0) for it in selected_items)
        revenue += total_rub
        total_items += len(selected_items)

        selected_indexes = []
        selected_names = []
        for it in selected_items:
            item_index = it.get("index")
            item_name = it.get("name", "")
            selected_indexes.append(item_index)
            selected_names.append(item_name)
            key = str(item_index)
            item_counts[key] = item_counts.get(key, 0) + 1

        orders.append(
            {
                "user_idx": user_idx,
                "user_id": user.get("user_id", user_idx),
                "selected_item_indexes": selected_indexes,
                "selected_item_names": selected_names,
                "estimated_total_rub": round(total_rub, 2),
            }
        )

    n_users = len(users)
    kpi = {
        "users_count": n_users,
        "total_revenue_rub": round(revenue, 2),
        "avg_check_rub": round(revenue / n_users, 2) if n_users else 0.0,
        "avg_items_per_order": round(total_items / n_users, 3) if n_users else 0.0,
        "item_counts": dict(sorted(item_counts.items(), key=lambda x: -x[1])),
    }
    return orders, kpi
