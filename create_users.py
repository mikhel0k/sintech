import argparse
import json
import random
from pathlib import Path
from typing import Dict, List, Set, Tuple


AGE_BUCKETS: List[Tuple[str, int, int]] = [
    ("age_0_17", 14, 17),
    ("age_18_24", 18, 24),
    ("age_25_34", 25, 34),
    ("age_35_44", 35, 44),
    ("age_45_54", 45, 54),
    ("age_55_plus", 55, 69),
]

DISTRICT_EFFECTS: Dict[str, Dict[str, float]] = {
    "Tsentralny": {"delivery_bias": 0.10, "avg_check_bias": 140, "car_ownership_bias": -0.05, "digital_bias": 0.08, "family_bias": -0.06, "factory_bias": -0.10},
    "Sovetsky": {"delivery_bias": 0.07, "avg_check_bias": 90, "car_ownership_bias": 0.00, "digital_bias": 0.06, "family_bias": -0.03, "factory_bias": -0.04},
    "Oktyabrsky": {"delivery_bias": 0.03, "avg_check_bias": 40, "car_ownership_bias": 0.02, "digital_bias": 0.04, "family_bias": 0.00, "factory_bias": -0.02},
    "Zheleznodorozhny": {"delivery_bias": 0.02, "avg_check_bias": 20, "car_ownership_bias": 0.01, "digital_bias": 0.02, "family_bias": 0.00, "factory_bias": -0.02},
    "Sverdlovsky": {"delivery_bias": -0.03, "avg_check_bias": -50, "car_ownership_bias": 0.04, "digital_bias": -0.03, "family_bias": 0.06, "factory_bias": 0.07},
    "Kirovsky": {"delivery_bias": -0.04, "avg_check_bias": -70, "car_ownership_bias": 0.05, "digital_bias": -0.04, "family_bias": 0.08, "factory_bias": 0.10},
    "Leninsky": {"delivery_bias": -0.06, "avg_check_bias": -90, "car_ownership_bias": 0.03, "digital_bias": -0.06, "family_bias": 0.10, "factory_bias": 0.12},
}

SOCIAL_COMPANY_TO_OCCASION: Dict[str, Dict[str, float]] = {
    "alone": {"quick_snack": 0.45, "full_meal": 0.40, "meeting_place": 0.10, "business_lunch": 0.05},
    "with_friends": {"quick_snack": 0.30, "full_meal": 0.35, "meeting_place": 0.30, "business_lunch": 0.05},
    "family_dinner": {"quick_snack": 0.25, "full_meal": 0.75},
    "business_meeting": {"meeting_place": 0.35, "business_lunch": 0.45, "full_meal": 0.20},
}

ROLE_TO_WORK: Dict[str, Dict[str, float]] = {
    "factory_worker": {"manufacturing_site": 0.70, "logistics_hub": 0.22, "service_sector": 0.05, "retail_store": 0.03},
    "office_worker": {"office": 0.68, "service_sector": 0.16, "public_sector": 0.10, "retail_store": 0.04, "remote": 0.02},
    "it_boy": {"it_office": 0.58, "remote": 0.30, "office": 0.12},
    "entrepreneur": {"small_business_owner": 0.62, "office": 0.20, "service_sector": 0.10, "retail_store": 0.08},
    "university_student": {"university": 0.80, "part_time_job": 0.15, "retail_store": 0.05},
    "school_student": {"school": 0.90, "university": 0.10},
}

ROLE_ALLOWED_WORK: Dict[str, Set[str]] = {
    "factory_worker": {"manufacturing_site", "logistics_hub", "service_sector", "retail_store"},
    "office_worker": {"office", "service_sector", "public_sector", "retail_store", "remote"},
    "it_boy": {"it_office", "remote", "office"},
    "entrepreneur": {"small_business_owner", "office", "service_sector", "retail_store"},
    "university_student": {"university", "part_time_job", "retail_store"},
    "school_student": {"school", "university"},
}

DIET_FORBIDDEN_CUISINES: Dict[str, Set[str]] = {
    "vegan": {"bbq"},
}

ARCHETYPE_ALLOWED_ROLES: Dict[str, Set[str]] = {
    "student_experimenter": {"university_student", "it_boy", "office_worker"},
    "young_digital_office": {"office_worker", "it_boy"},
    "family_pragmatic_worker": {"factory_worker", "office_worker", "entrepreneur"},
    "mature_conservative_factory": {"factory_worker", "office_worker"},
    "premium_entrepreneur": {"entrepreneur", "office_worker"},
    "single_low_budget_worker": {"factory_worker", "office_worker", "university_student"},
    "health_oriented_parent": {"office_worker", "entrepreneur", "it_boy"},
    "social_city_explorer": {"office_worker", "entrepreneur", "university_student", "it_boy"},
}

ARCHETYPE_ALLOWED_WORK: Dict[str, Set[str]] = {
    "student_experimenter": {"university", "part_time_job", "retail_store", "it_office", "office"},
    "young_digital_office": {"office", "it_office", "remote", "service_sector"},
    "family_pragmatic_worker": {"manufacturing_site", "logistics_hub", "service_sector", "office", "retail_store"},
    "mature_conservative_factory": {"manufacturing_site", "logistics_hub", "service_sector", "retail_store"},
    "premium_entrepreneur": {"small_business_owner", "office", "service_sector", "retail_store"},
    "single_low_budget_worker": {"manufacturing_site", "logistics_hub", "service_sector", "retail_store", "office", "part_time_job"},
    "health_oriented_parent": {"office", "remote", "service_sector", "small_business_owner", "public_sector"},
    "social_city_explorer": {"office", "service_sector", "retail_store", "small_business_owner", "it_office", "remote"},
}

ARCHETYPE_EXPECTED_DIGITAL: Dict[str, Set[str]] = {
    "student_experimenter": {"high", "medium"},
    "young_digital_office": {"high", "medium"},
    "family_pragmatic_worker": {"medium", "low"},
    "mature_conservative_factory": {"low", "medium"},
    "premium_entrepreneur": {"high", "medium"},
    "single_low_budget_worker": {"medium", "low"},
    "health_oriented_parent": {"medium", "high"},
    "social_city_explorer": {"high", "medium"},
}

DIGITAL_TO_CHANNEL: Dict[str, Dict[str, float]] = {
    "high": {"delivery_app": 0.42, "direct_app": 0.36, "in_store": 0.18, "phone_order": 0.04},
    "medium": {"delivery_app": 0.34, "direct_app": 0.24, "in_store": 0.30, "phone_order": 0.12},
    "low": {"delivery_app": 0.14, "direct_app": 0.08, "in_store": 0.48, "phone_order": 0.30},
}

DIET_CUISINE_SCORES: Dict[str, Dict[str, float]] = {
    "fast_food": {"burgers": 1.0, "pizza": 0.9, "street_food": 0.9, "bbq": 0.6, "healthy": 0.2, "cafe": 0.3, "asian": 0.4, "premium_casual": 0.2, "russian": 0.4},
    "healthy_lifestyle": {"healthy": 1.0, "cafe": 0.8, "asian": 0.7, "premium_casual": 0.5, "russian": 0.4, "pizza": 0.2, "burgers": 0.1, "street_food": 0.15, "bbq": 0.25},
    "vegan": {"healthy": 1.0, "asian": 0.8, "cafe": 0.8, "premium_casual": 0.5, "russian": 0.3, "pizza": 0.25, "street_food": 0.3, "bbq": 0.01, "burgers": 0.05},
    "high_protein": {"bbq": 0.9, "healthy": 0.8, "asian": 0.6, "russian": 0.5, "cafe": 0.4, "pizza": 0.3, "burgers": 0.35, "street_food": 0.3, "premium_casual": 0.35},
    "halal": {"asian": 0.8, "cafe": 0.6, "russian": 0.5, "street_food": 0.7, "healthy": 0.5, "pizza": 0.4, "burgers": 0.4, "bbq": 0.4, "premium_casual": 0.3},
}


def weighted_choice(options: List[Tuple[str, float]]) -> str:
    values, weights = zip(*options)
    return random.choices(values, weights=weights, k=1)[0]


def _sample_truncated_gauss(low: int, high: int, mean: float, stdev: float) -> int:
    for _ in range(20):
        x = int(round(random.gauss(mean, stdev)))
        if low <= x <= high:
            return x
    return max(low, min(high, int(round(mean))))


def pick_age(age_dist: Dict[str, float], min_age: int, max_age: int) -> int:
    options = [(bucket, float(age_dist.get(bucket, 0))) for bucket, _, _ in AGE_BUCKETS]
    total = sum(weight for _, weight in options)
    if total <= 0:
        return random.randint(18, 60)
    bucket_name = weighted_choice(options)
    median_age = int(age_dist.get("median_age", 37))
    for key, low, high in AGE_BUCKETS:
        if key == bucket_name:
            low = max(low, min_age)
            high = min(high, max_age)
            if low > high:
                return random.randint(min_age, max_age)
            center = (low + high) / 2
            mean = 0.7 * center + 0.3 * median_age
            stdev = max(1.8, (high - low) / 4)
            return _sample_truncated_gauss(low, high, mean, stdev)
    return random.randint(min_age, max_age)


def pick_income(base_income: int, sensitivity: str) -> int:
    stdev_map = {
        "low": 0.18,
        "medium_to_low": 0.20,
        "medium": 0.25,
        "medium_to_above_medium": 0.28,
        "above_medium": 0.30,
        "high": 0.35,
    }
    stdev = stdev_map.get(sensitivity, 0.28)
    val = int(random.gauss(base_income, max(1000, base_income * stdev)))
    return max(12000, val)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def sample_poisson(lam: float) -> int:
    """Poisson sampler without numpy (Knuth algorithm)."""
    lam = max(0.0001, lam)
    l = pow(2.718281828459045, -lam)
    k = 0
    p = 1.0
    while p > l:
        k += 1
        p *= random.random()
    return max(0, k - 1)


def pick_archetype(age: int, income_hint: int, district: str) -> str:
    effects = DISTRICT_EFFECTS.get(district, {})
    factory_boost = max(0.0, effects.get("factory_bias", 0.0))
    if age <= 24:
        return weighted_choice([("student_experimenter", 0.30), ("young_digital_office", 0.28), ("single_low_budget_worker", 0.30 + factory_boost), ("social_city_explorer", 0.12)])
    if income_hint > 90000:
        return weighted_choice([("premium_entrepreneur", 0.32), ("young_digital_office", 0.26), ("health_oriented_parent", 0.16), ("social_city_explorer", 0.26)])
    if age >= 45:
        return weighted_choice([("mature_conservative_factory", 0.34 + factory_boost), ("family_pragmatic_worker", 0.40), ("health_oriented_parent", 0.18), ("single_low_budget_worker", 0.08)])
    return weighted_choice([("family_pragmatic_worker", 0.34), ("young_digital_office", 0.20), ("single_low_budget_worker", 0.22 + factory_boost), ("health_oriented_parent", 0.12), ("social_city_explorer", 0.12)])


def build_latent(archetype: str, district: str) -> Dict[str, float]:
    base = {
        "budget_mode": weighted_choice([("tight", 0.30), ("balanced", 0.50), ("comfortable", 0.20)]),
        "routine_mode": weighted_choice([("routine", 0.40), ("mixed", 0.40), ("novelty", 0.20)]),
        "delivery_affinity": 0.5,
        "health_orientation": 0.45,
        "family_centricity": 0.45,
        "social_outgoingness": 0.45,
    }
    by_arch = {
        "student_experimenter": (0.62, 0.35, 0.78, 0.70),
        "young_digital_office": (0.70, 0.45, 0.42, 0.58),
        "family_pragmatic_worker": (0.42, 0.64, 0.72, 0.40),
        "mature_conservative_factory": (0.28, 0.30, 0.78, 0.24),
        "premium_entrepreneur": (0.66, 0.40, 0.36, 0.62),
        "single_low_budget_worker": (0.30, 0.22, 0.28, 0.35),
        "health_oriented_parent": (0.52, 0.84, 0.80, 0.32),
        "social_city_explorer": (0.74, 0.38, 0.30, 0.82),
    }
    if archetype in by_arch:
        base["delivery_affinity"], base["health_orientation"], base["family_centricity"], base["social_outgoingness"] = by_arch[archetype]
    effects = DISTRICT_EFFECTS.get(district, {})
    base["delivery_affinity"] = clamp(base["delivery_affinity"] + effects.get("delivery_bias", 0.0), 0.02, 0.98)
    base["social_outgoingness"] = clamp(base["social_outgoingness"] + effects.get("digital_bias", 0.0) * 0.4, 0.02, 0.98)
    base["family_centricity"] = clamp(base["family_centricity"] + effects.get("family_bias", 0.0), 0.02, 0.98)
    return base


def income_band_from_value(income: int) -> str:
    if income < 40000:
        return "low"
    if income < 70000:
        return "middle"
    if income < 110000:
        return "upper_middle"
    return "high"


def pick_home_location(base_home: str) -> str:
    base = base_home.lower()
    if "mixed apartment and private housing" in base:
        options = [
            ("apartment_block", 0.52),
            ("private_house", 0.33),
            ("new_residential_complex", 0.15),
        ]
    elif "dense central urban housing" in base:
        options = [
            ("central_apartment_block", 0.55),
            ("business_center_area_housing", 0.25),
            ("new_residential_complex", 0.20),
        ]
    else:
        options = [
            ("apartment_block", 0.6),
            ("new_residential_complex", 0.2),
            ("private_house", 0.2),
        ]
    return weighted_choice(options)


def pick_work_location(
    base_work: str,
    age: int,
    primary_role: str,
    employment_status: str,
    archetype: str,
    district: str,
) -> str:
    base = base_work.lower()
    if employment_status in {"unemployed", "retired"}:
        return "none"
    if age < 18:
        return weighted_choice([("school", 0.75), ("college_prep", 0.25)])
    district_effects = DISTRICT_EFFECTS.get(district, {})
    role_scores = dict(ROLE_TO_WORK.get(primary_role, {"office": 1.0}))
    # District/base-work adjustment layered over strict role priors.
    if "manufacturing" in base:
        role_scores["manufacturing_site"] = role_scores.get("manufacturing_site", 0.0) + 0.10
        role_scores["logistics_hub"] = role_scores.get("logistics_hub", 0.0) + 0.04
    if "offices" in base or "business" in base:
        role_scores["office"] = role_scores.get("office", 0.0) + 0.10
        role_scores["service_sector"] = role_scores.get("service_sector", 0.0) + 0.03
    if "education" in base:
        role_scores["public_sector"] = role_scores.get("public_sector", 0.0) + 0.08
    if primary_role == "factory_worker":
        role_scores["manufacturing_site"] = role_scores.get("manufacturing_site", 0.0) + max(0.0, district_effects.get("factory_bias", 0.0))
    if primary_role == "entrepreneur" and archetype == "premium_entrepreneur":
        role_scores["small_business_owner"] = role_scores.get("small_business_owner", 0.0) + 0.10
    if employment_status == "student":
        role_scores["university"] = role_scores.get("university", 0.0) + 0.10
        role_scores["part_time_job"] = role_scores.get("part_time_job", 0.0) + 0.05
    allowed = ROLE_ALLOWED_WORK.get(primary_role, {"office"})
    role_scores = {k: v for k, v in role_scores.items() if k in allowed}
    if not role_scores:
        role_scores = {"office": 1.0}
    return weighted_choice(list(normalize_probs(role_scores).items()))


def sample_height_weight(sex: str, age: int) -> Dict[str, float]:
    if sex == "male":
        height = clamp(random.gauss(178, 7), 160, 198)
        bmi = clamp(random.gauss(26 if age > 40 else 24.5, 3.2), 18, 38)
    else:
        height = clamp(random.gauss(165, 6.5), 148, 186)
        bmi = clamp(random.gauss(25 if age > 40 else 23.8, 3.5), 17, 40)
    weight = bmi * ((height / 100) ** 2)
    if bmi < 20.5:
        build = "slim"
    elif bmi < 27.5:
        build = "average"
    else:
        build = "overweight"
    return {
        "height_cm": round(height, 1),
        "weight_kg": round(weight, 1),
        "body_build": build,
        "bmi": round(bmi, 1),
    }


def infer_education(age: int) -> str:
    if age <= 20:
        return weighted_choice([("secondary", 0.55), ("vocational", 0.30), ("incomplete_higher", 0.15)])
    if age <= 24:
        return weighted_choice([("vocational", 0.35), ("higher", 0.40), ("incomplete_higher", 0.25)])
    return weighted_choice([("secondary", 0.20), ("vocational", 0.33), ("higher", 0.44), ("postgraduate", 0.03)])


def infer_family(age: int, sex: str, archetype: str) -> Dict[str, object]:
    if age <= 22:
        status = weighted_choice([("single", 0.86), ("partnered", 0.12), ("married", 0.02)])
    elif age <= 30:
        status = weighted_choice([("single", 0.44), ("partnered", 0.28), ("married", 0.28)])
    elif age <= 45:
        status = weighted_choice([("single", 0.20), ("partnered", 0.18), ("married", 0.56), ("divorced", 0.06)])
    else:
        status = weighted_choice([("single", 0.18), ("married", 0.57), ("divorced", 0.17), ("widowed", 0.08)])

    # Archetype-aware family tendency
    family_bias = 0.0
    single_bias = 0.0
    if archetype in {"family_pragmatic_worker", "health_oriented_parent", "mature_conservative_factory"}:
        family_bias += 0.08
    if archetype in {"social_city_explorer", "premium_entrepreneur", "young_digital_office"}:
        single_bias += 0.06
    if single_bias > 0 and status in {"married", "partnered"} and random.random() < single_bias:
        status = weighted_choice([("single", 0.75), ("partnered", 0.25)])
    if family_bias > 0 and status == "single" and age >= 28 and random.random() < family_bias:
        status = weighted_choice([("partnered", 0.4), ("married", 0.6)])

    children = 0
    if status in {"married", "partnered", "divorced"} and age >= 24:
        parent_bias = 0.06 if sex == "female" and 24 <= age <= 40 else 0.0
        if age <= 30:
            children = random.choices([0, 1, 2, 3], weights=[0.45 - parent_bias, 0.35, 0.16 + parent_bias * 0.6, 0.04 + parent_bias * 0.4], k=1)[0]
        elif age <= 45:
            children = random.choices([0, 1, 2, 3, 4], weights=[0.18, 0.33, 0.31, 0.13, 0.05], k=1)[0]
        else:
            children = random.choices([0, 1, 2, 3, 4], weights=[0.15, 0.32, 0.31, 0.16, 0.06], k=1)[0]
        if family_bias > 0 and random.random() < min(0.25, family_bias):
            children = min(4, children + 1)

    hh_size = 1
    if status == "single":
        hh_size = random.choices([1, 2], weights=[0.82, 0.18], k=1)[0]
    elif status == "partnered":
        hh_size = 2 + children + random.choices([0, 1], weights=[0.8, 0.2], k=1)[0]
    elif status == "married":
        hh_size = 2 + children + random.choices([0, 1, 2], weights=[0.65, 0.25, 0.10], k=1)[0]
    else:
        hh_size = 1 + children + random.choices([0, 1], weights=[0.75, 0.25], k=1)[0]

    infant_prob = 0.0
    if children > 0:
        # Infant children are realistic mainly for younger parent cohorts.
        if 22 <= age <= 32:
            infant_prob = 0.30
        elif 33 <= age <= 40:
            infant_prob = 0.14
        elif 41 <= age <= 45:
            infant_prob = 0.03
        else:
            infant_prob = 0.0

    return {
        "marital_status": status,
        "children_count": children,
        "household_size": min(8, hh_size),
        "is_parent": children > 0,
        "has_infant_child": children > 0 and random.random() < infant_prob,
    }


def normalize_probs(counter: Dict[str, float]) -> Dict[str, float]:
    total = sum(max(0.0, v) for v in counter.values())
    if total <= 0:
        n = len(counter) or 1
        return {k: 1.0 / n for k in counter}
    return {k: max(0.0, v) / total for k, v in counter.items()}


def infer_life_stage(age: int, family: Dict[str, object], roles: List[str]) -> str:
    if age <= 22:
        return "youth"
    if "university_student" in roles:
        return "student"
    if bool(family.get("has_infant_child")):
        return "young_parent"
    if age <= 35:
        return "early_career"
    if age <= 50:
        return "family_career"
    if age <= 60:
        return "mature"
    return "pre_retiree"


def infer_employment(age: int, primary_role: str, life_stage: str) -> Dict[str, object]:
    if age < 20:
        return {"status": "student", "schedule": "daytime", "remote_share": 0.0}
    if primary_role == "entrepreneur":
        return {"status": "self_employed", "schedule": weighted_choice([("fixed", 0.35), ("flexible", 0.65)]), "remote_share": round(random.uniform(0.1, 0.6), 2)}
    if primary_role == "factory_worker":
        return {"status": "employed", "schedule": weighted_choice([("shift", 0.75), ("fixed", 0.25)]), "remote_share": 0.0}
    if primary_role in {"office_worker", "it_boy"}:
        rem = random.uniform(0.25, 0.95) if primary_role == "it_boy" else random.uniform(0.0, 0.55)
        return {"status": "employed", "schedule": weighted_choice([("fixed", 0.7), ("hybrid", 0.3)]), "remote_share": round(rem, 2)}
    if primary_role == "university_student":
        return {"status": "student", "schedule": weighted_choice([("daytime", 0.7), ("flexible", 0.3)]), "remote_share": 0.0}
    if life_stage == "pre_retiree" and random.random() < 0.2:
        return {"status": "retired", "schedule": "free", "remote_share": 0.0}
    return {"status": weighted_choice([("employed", 0.82), ("self_employed", 0.08), ("unemployed", 0.10)]), "schedule": weighted_choice([("fixed", 0.6), ("shift", 0.15), ("flexible", 0.25)]), "remote_share": round(random.uniform(0.0, 0.4), 2)}


def adjust_income_with_factors(base_income: int, age: int, roles: List[str], employment: Dict[str, object], education: str) -> int:
    income = float(base_income)
    if employment["status"] == "student":
        income *= random.uniform(0.35, 0.7)
    elif employment["status"] == "retired":
        income *= random.uniform(0.45, 0.75)
    elif employment["status"] == "unemployed":
        income *= random.uniform(0.25, 0.55)
    elif employment["status"] == "self_employed":
        income *= random.uniform(0.9, 1.45)

    if "it_boy" in roles:
        income *= random.uniform(1.15, 1.65)
    if "factory_worker" in roles:
        income *= random.uniform(0.9, 1.2)
    if "office_worker" in roles:
        income *= random.uniform(0.95, 1.25)
    if "entrepreneur" in roles:
        income *= random.uniform(1.0, 1.9)

    if education == "higher":
        income *= 1.08
    elif education == "postgraduate":
        income *= 1.18
    elif education == "secondary":
        income *= 0.92

    if age < 23:
        income *= random.uniform(0.55, 0.95)
    elif age > 58:
        income *= random.uniform(0.75, 1.0)

    return int(clamp(income, 12000, 260000))


def pick_transport_and_commute(age: int, income: int, district: str) -> Dict[str, object]:
    effects = DISTRICT_EFFECTS.get(district, {})
    car_prob = 0.28 + (0.14 if income > 80000 else 0.0) + (0.12 if age >= 30 else 0.0)
    car_prob += effects.get("car_ownership_bias", 0.0)
    car_prob = clamp(car_prob, 0.10, 0.85)
    has_car = random.random() < car_prob
    main_transport = weighted_choice(
        [("car", 0.68), ("public_transport", 0.22), ("taxi", 0.08), ("walk", 0.02)]
    ) if has_car else weighted_choice(
        [("public_transport", 0.60), ("walk", 0.20), ("taxi", 0.12), ("carsharing", 0.08)]
    )
    district_base_commute = {
        "Tsentralny": 28,
        "Sovetsky": 30,
        "Oktyabrsky": 33,
        "Zheleznodorozhny": 32,
        "Sverdlovsky": 36,
        "Kirovsky": 37,
        "Leninsky": 38,
    }
    base_minutes = random.gauss(district_base_commute.get(district, 34), 11)
    return {
        "has_car": has_car,
        "main_transport": main_transport,
        "commute_minutes_one_way": int(clamp(base_minutes, 8, 95)),
    }


def pick_channels(
    age: int,
    income: int,
    life_stage: str,
    latent: Dict[str, float],
    transport: Dict[str, object],
    household: Dict[str, object],
    district: str,
) -> Dict[str, object]:
    effects = DISTRICT_EFFECTS.get(district, {})
    high_prob = clamp(
        0.20
        + (0.26 if age < 35 else -0.05)
        + (0.10 if latent["routine_mode"] == "novelty" else 0.0)
        + effects.get("digital_bias", 0.0),
        0.05,
        0.85,
    )
    low_prob = clamp(0.18 + (0.10 if age > 55 else 0.0), 0.05, 0.60)
    medium_prob = max(0.05, 1.0 - high_prob - low_prob)
    digital_intensity = weighted_choice(
        [("high", high_prob), ("medium", medium_prob), ("low", low_prob)]
    )

    scores = dict(DIGITAL_TO_CHANNEL[digital_intensity])
    scores["delivery_app"] += latent["delivery_affinity"] * 0.22
    scores["direct_app"] += latent["delivery_affinity"] * 0.10
    scores["in_store"] += 0.10 if transport["main_transport"] in {"car", "walk"} else -0.03
    scores["delivery_app"] += effects.get("delivery_bias", 0.0)
    if household["children_count"] >= 2:
        scores["delivery_app"] += 0.10
    if life_stage in {"student", "youth"}:
        scores["delivery_app"] += 0.08
        scores["direct_app"] += 0.06
        scores["phone_order"] -= 0.08
    if income > 90000:
        scores["direct_app"] += 0.08
    scores = normalize_probs(scores)
    channel = weighted_choice(list(scores.items()))
    prefers_delivery = channel in {"delivery_app", "direct_app"}
    if channel == "phone_order" and digital_intensity == "high":
        channel = weighted_choice([("direct_app", 0.72), ("delivery_app", 0.28)])
        prefers_delivery = True
    return {"primary_order_channel": channel, "prefers_delivery": prefers_delivery, "digital_intensity": digital_intensity}


def pick_meal_behavior(
    age: int,
    income: int,
    family: Dict[str, object],
    social: Dict[str, str],
    channels: Dict[str, object],
    psychographics: Dict[str, str],
    life_stage: str,
    diet_profile: str,
    district: str,
    archetype: str,
    food_preferences: Dict[str, object],
    behavior_habits: Dict[str, object],
) -> Dict[str, object]:
    effects = DISTRICT_EFFECTS.get(district, {})
    lam = 1.6 + (0.7 if income > 80000 else 0.0) + (0.8 if channels["prefers_delivery"] else 0.0)
    if life_stage in {"student", "youth"}:
        lam += 0.5
    if psychographics["price_sensitivity"] == "high":
        lam -= 0.3
    if family["children_count"] >= 2:
        lam += 0.4
    if archetype == "student_experimenter":
        lam += 0.35
    elif archetype == "premium_entrepreneur":
        lam += 0.15
    elif archetype == "single_low_budget_worker":
        lam -= 0.25

    zero_prob = clamp(
        0.20
        + (0.10 if psychographics["price_sensitivity"] == "high" else 0.0)
        - (0.06 if channels["prefers_delivery"] else 0.0)
        + (0.06 if archetype == "single_low_budget_worker" else 0.0)
        - (0.04 if archetype == "student_experimenter" else 0.0),
        0.05,
        0.50,
    )
    if random.random() < zero_prob:
        weekly_orders = 0
    else:
        weekly_orders = max(1, min(14, sample_poisson(max(0.4, lam))))
    avg_check = 560 + 0.0075 * income + effects.get("avg_check_bias", 0.0)
    if social["occasion"] == "full_meal":
        avg_check += 120
    if family["children_count"] >= 2:
        avg_check *= 1.18
    if life_stage in {"student", "youth"}:
        avg_check *= 0.82
    if psychographics["price_sensitivity"] in {"high", "medium_to_high"}:
        avg_check *= 0.9
    if psychographics["brand_loyalty"] == "high":
        avg_check *= 1.08
    if diet_profile in {"high_protein", "healthy_lifestyle"}:
        avg_check *= 1.04
    if archetype == "premium_entrepreneur":
        avg_check *= 1.16
    elif archetype == "student_experimenter":
        avg_check *= 0.84
    elif archetype == "single_low_budget_worker":
        avg_check *= 0.88

    portion = food_preferences.get("portion_preference", "medium")
    if portion == "large":
        avg_check *= 1.12
    elif portion == "small":
        avg_check *= 0.92

    if behavior_habits.get("group_ordering_tendency") == "high":
        avg_check *= 1.08
    if behavior_habits.get("routine_vs_novelty") == "novelty":
        avg_check *= 1.03
    avg_check = int(clamp(random.gauss(avg_check, 145), 220, 2600))
    if weekly_orders == 0:
        avg_check = None
    coupon = "high" if psychographics["price_sensitivity"] in {"high", "medium_to_high"} else weighted_choice([("medium", 0.7), ("low", 0.3)])
    if archetype == "premium_entrepreneur":
        coupon = weighted_choice([("low", 0.75), ("medium", 0.25)])
    elif archetype == "student_experimenter":
        coupon = weighted_choice([("high", 0.68), ("medium", 0.30), ("low", 0.02)])

    openness = "high" if psychographics["innovativeness"] in {"high", "medium_to_high"} else weighted_choice([("medium", 0.72), ("low", 0.28)])
    if archetype == "student_experimenter":
        openness = weighted_choice([("high", 0.72), ("medium", 0.25), ("low", 0.03)])
    elif archetype in {"mature_conservative_factory", "family_pragmatic_worker"}:
        openness = weighted_choice([("low", 0.40), ("medium", 0.52), ("high", 0.08)])
    return {"orders_per_week": weekly_orders, "avg_order_check_rub": avg_check, "coupon_sensitivity": coupon, "new_menu_openness": openness}


def normalize_employment_and_work(employment: Dict[str, object], work_location_type: str, primary_role: str, age: int) -> Tuple[Dict[str, object], str]:
    e = dict(employment)
    w = work_location_type
    if e["status"] == "unemployed":
        w = "none"
        e["schedule"] = "free"
        e["remote_share"] = 0.0
    if e["status"] == "student":
        if primary_role == "university_student":
            w = "university"
        e["schedule"] = weighted_choice([("daytime", 0.7), ("flexible", 0.3)])
        e["remote_share"] = 0.0
    if e["status"] == "retired":
        w = "none"
        e["schedule"] = "free"
        e["remote_share"] = 0.0
    if primary_role == "factory_worker":
        e["remote_share"] = 0.0
        if e["schedule"] not in {"shift", "fixed"}:
            e["schedule"] = "shift"
        if w not in {"manufacturing_site", "logistics_hub"}:
            w = weighted_choice([("manufacturing_site", 0.85), ("logistics_hub", 0.15)])
    if primary_role in {"office_worker", "it_boy"} and e["status"] == "employed" and w == "none":
        w = "office" if primary_role == "office_worker" else "it_office"
    if primary_role == "it_boy":
        if w not in {"it_office", "remote", "office"}:
            w = weighted_choice([("it_office", 0.62), ("remote", 0.28), ("office", 0.10)])
    if age < 20:
        e["status"] = "student"
        e["schedule"] = "daytime"
        e["remote_share"] = 0.0
        if primary_role != "school_student":
            w = "university" if primary_role == "university_student" else "school"
    return e, w


def pick_psychographics(age: int, income: int, life_stage: str, latent: Dict[str, float]) -> Dict[str, str]:
    # Build explicit segments to avoid template-like uniformity.
    if life_stage in {"student", "youth"}:
        segment = weighted_choice([("experimenter", 0.36), ("budget", 0.34), ("social", 0.30)])
    elif income > 90000:
        segment = weighted_choice([("premium", 0.38), ("experimenter", 0.24), ("pragmatic", 0.38)])
    elif age > 50:
        segment = weighted_choice([("conservative", 0.45), ("pragmatic", 0.40), ("budget", 0.15)])
    else:
        segment = weighted_choice([("pragmatic", 0.34), ("budget", 0.25), ("social", 0.21), ("experimenter", 0.20)])

    mapping = {
        "budget": {"brand_loyalty": "low", "innovativeness": "low", "price_sensitivity": "high"},
        "premium": {"brand_loyalty": "high", "innovativeness": "medium_to_high", "price_sensitivity": "low"},
        "experimenter": {"brand_loyalty": "medium", "innovativeness": "high", "price_sensitivity": "medium"},
        "conservative": {"brand_loyalty": "high", "innovativeness": "low", "price_sensitivity": "medium"},
        "pragmatic": {"brand_loyalty": "medium", "innovativeness": "medium", "price_sensitivity": "medium_to_high"},
        "social": {"brand_loyalty": "medium_to_high", "innovativeness": "medium_to_high", "price_sensitivity": "medium"},
    }
    psy = mapping[segment]
    if latent["budget_mode"] == "tight":
        psy["price_sensitivity"] = "high"
    if latent["routine_mode"] == "novelty":
        psy["innovativeness"] = weighted_choice([("medium_to_high", 0.4), ("high", 0.6)])
    if latent["routine_mode"] == "routine":
        psy["innovativeness"] = weighted_choice([("low", 0.55), ("medium", 0.45)])
    # Small jitter for extra heterogeneity.
    if random.random() < 0.08:
        psy = dict(psy)
        psy["price_sensitivity"] = weighted_choice([("low", 0.2), ("medium", 0.45), ("medium_to_high", 0.35)])
    return psy


def lifestyle_roles(d: Dict[str, float], sex: str, age: int, archetype: str, family: Dict[str, object]) -> Dict[str, object]:
    primary_options = []
    for role in ["factory_worker", "office_worker", "entrepreneur", "it_boy", "university_student", "school_student"]:
        p = float(d.get(role, 0.0))
        if role == "school_student" and not (14 <= age <= 18):
            continue
        if role == "university_student" and not (17 <= age <= 27):
            continue
        if role in {"office_worker", "factory_worker"} and age < 20:
            continue
        if role == "entrepreneur" and age < 23:
            continue
        if role == "it_boy" and (sex != "male" or not (20 <= age <= 40)):
            continue
        if archetype in {"student_experimenter"} and role == "university_student":
            p *= 1.8
        if archetype in {"mature_conservative_factory", "single_low_budget_worker"} and role == "factory_worker":
            p *= 1.5
        if archetype in {"young_digital_office"} and role in {"office_worker", "it_boy"}:
            p *= 1.4
        if archetype in {"premium_entrepreneur"} and role == "entrepreneur":
            p *= 1.8
        primary_options.append((role, max(0.001, p)))
    primary_role = weighted_choice(primary_options or [("office_worker", 1.0)])

    secondary_roles: List[str] = []
    if sex == "female" and 22 <= age <= 45 and family.get("has_infant_child"):
        if random.random() < 0.72:
            secondary_roles.append("maternity_mom")
    if int(family.get("children_count", 0)) >= 2 and 25 <= age <= 55:
        if random.random() < 0.7:
            secondary_roles.append("large_family")
    if sex == "female" and 16 <= age <= 35 and random.random() < float(d.get("instagram_girl", 0.0)):
        secondary_roles.append("instagram_girl")

    return {"primary_role": primary_role, "secondary_roles": secondary_roles}


def pick_daypart(d: Dict[str, float]) -> str:
    return weighted_choice(
        [
            ("breakfast", float(d.get("breakfast", 0.2))),
            ("lunch", float(d.get("lunch", 0.35))),
            ("dinner", float(d.get("dinner", 0.45))),
        ]
    )


def pick_social_context(
    d: Dict[str, float],
    age: int,
    household: Dict[str, object],
    employment_status: str,
    primary_role: str,
    latent: Dict[str, float],
) -> Dict[str, str]:
    company_options = {
        "alone": float(d.get("alone", 0.25)),
        "with_friends": float(d.get("with_friends", 0.25)),
        "business_meeting": float(d.get("business_meeting", 0.15)),
        "family_dinner": float(d.get("family_dinner", 0.35)),
    }
    if age < 23:
        company_options.pop("business_meeting", None)
    if employment_status in {"student", "unemployed", "retired"}:
        company_options["business_meeting"] = company_options.get("business_meeting", 0.0) * 0.12
    if household["household_size"] <= 1 and household["children_count"] == 0:
        company_options["family_dinner"] = company_options.get("family_dinner", 0.0) * 0.08
    if household["children_count"] >= 2:
        company_options["family_dinner"] = company_options.get("family_dinner", 0.0) * 1.5
    if primary_role in {"office_worker", "entrepreneur", "it_boy"} and employment_status in {"employed", "self_employed"}:
        company_options["business_meeting"] = company_options.get("business_meeting", 0.0) * 1.25
    if latent["social_outgoingness"] > 0.65:
        company_options["with_friends"] = company_options.get("with_friends", 0.0) * 1.35
    if latent["family_centricity"] > 0.65:
        company_options["family_dinner"] = company_options.get("family_dinner", 0.0) * 1.4
    company = weighted_choice(list(normalize_probs(company_options).items()))
    occasion_scores = dict(SOCIAL_COMPANY_TO_OCCASION.get(company, {"full_meal": 1.0}))
    if employment_status in {"student", "unemployed", "retired"}:
        occasion_scores["business_lunch"] = occasion_scores.get("business_lunch", 0.0) * 0.08
    if age < 23:
        occasion_scores["business_lunch"] = occasion_scores.get("business_lunch", 0.0) * 0.05
    if household["children_count"] >= 2:
        occasion_scores["full_meal"] = occasion_scores.get("full_meal", 0.0) * 1.2
        occasion_scores["quick_snack"] = occasion_scores.get("quick_snack", 0.0) * 1.1
    occasion = weighted_choice(list(normalize_probs(occasion_scores).items()))
    return {"company": company, "occasion": occasion}


def pick_diet(d: Dict[str, float], latent: Dict[str, float], health_propensity: float) -> str:
    probs = {
        "healthy_lifestyle": float(d.get("healthy_lifestyle", 0.3)),
        "fast_food": float(d.get("fast_food", 0.4)),
        "vegan": float(d.get("vegan", 0.02)),
        "high_protein": float(d.get("high_protein", 0.15)),
        "halal": float(d.get("halal", 0.05)),
    }
    probs["healthy_lifestyle"] *= (0.7 + health_propensity)
    probs["fast_food"] *= (1.15 - health_propensity)
    if latent["routine_mode"] == "novelty":
        probs["vegan"] *= 1.7
    if latent["budget_mode"] == "tight":
        probs["fast_food"] *= 1.2
        probs["healthy_lifestyle"] *= 0.9
    return weighted_choice(list(normalize_probs(probs).items()))


def pick_food_allergies(age: int) -> Dict[str, bool]:
    # Baseline prevalence for synthetic population.
    p_lactose = 0.14
    p_gluten = 0.03
    p_nuts = 0.02

    # Small age effects.
    if age < 22:
        p_lactose += 0.02
        p_nuts += 0.01
    elif age > 50:
        p_gluten += 0.01

    p_lactose = max(0.01, min(0.35, p_lactose))
    p_gluten = max(0.005, min(0.12, p_gluten))
    p_nuts = max(0.005, min(0.10, p_nuts))

    return {
        "lactose": random.random() < p_lactose,
        "gluten": random.random() < p_gluten,
        "nuts": random.random() < p_nuts,
    }


def pick_health_restrictions(allergies: Dict[str, bool], age: int, income: int) -> Dict[str, bool]:
    low_sugar = random.random() < (0.08 + (0.06 if age > 45 else 0.0))
    low_salt = random.random() < (0.07 + (0.07 if age > 50 else 0.0))
    no_pork = random.random() < (0.06 + (0.02 if income > 80000 else 0.0))
    no_lactose = allergies["lactose"] or random.random() < 0.03
    return {
        "low_sugar": low_sugar,
        "low_salt": low_salt,
        "no_pork": no_pork,
        "no_lactose": no_lactose,
    }


def pick_food_preferences_by_archetype(
    archetype: str,
    diet_profile: str,
    psychographics: Dict[str, str],
    latent: Dict[str, float],
    district: str,
) -> Dict[str, object]:
    archetype_map = {
        "student_experimenter": ["burgers", "pizza", "asian", "street_food"],
        "young_digital_office": ["asian", "cafe", "healthy", "pizza"],
        "family_pragmatic_worker": ["pizza", "bbq", "russian", "burgers"],
        "mature_conservative_factory": ["russian", "bbq", "cafe", "asian"],
        "premium_entrepreneur": ["healthy", "asian", "cafe", "premium_casual"],
        "single_low_budget_worker": ["burgers", "pizza", "street_food", "russian"],
        "health_oriented_parent": ["healthy", "cafe", "asian", "russian"],
        "social_city_explorer": ["asian", "cafe", "street_food", "premium_casual"],
    }
    pool = archetype_map.get(archetype, ["russian", "asian", "pizza", "cafe"])
    base_scores = {c: 0.15 for c in ["russian", "asian", "burgers", "pizza", "cafe", "bbq", "healthy", "street_food", "premium_casual"]}
    for c in pool:
        base_scores[c] = base_scores.get(c, 0.15) + 0.5
    diet_scores = DIET_CUISINE_SCORES.get(diet_profile, {})
    for c, s in diet_scores.items():
        base_scores[c] = base_scores.get(c, 0.15) + s
    for forbidden in DIET_FORBIDDEN_CUISINES.get(diet_profile, set()):
        base_scores.pop(forbidden, None)
    # sample 3 unique cuisines by score
    preferred = []
    tmp = dict(base_scores)
    for _ in range(3):
        c = weighted_choice(list(normalize_probs(tmp).items()))
        preferred.append(c)
        tmp.pop(c, None)

    avoided = []
    if diet_profile == "vegan":
        avoided += ["bbq", "meat_heavy", "dairy_heavy"]
    if diet_profile == "halal":
        avoided += ["pork_heavy"]
    if psychographics["price_sensitivity"] in {"high", "medium_to_high"}:
        avoided += ["premium_only"]
    if district in {"Tsentralny", "Sovetsky"} and random.random() < 0.35:
        preferred = list(dict.fromkeys(preferred + ["cafe"]))[:3]
    portion = weighted_choice([("small", 0.24), ("medium", 0.58), ("large", 0.18)])
    if archetype in {"family_pragmatic_worker", "mature_conservative_factory"}:
        portion = weighted_choice([("small", 0.12), ("medium", 0.52), ("large", 0.36)])
    flavors = random.sample(["savory", "spicy", "mild", "sweet"], k=2)
    if archetype in {"health_oriented_parent", "premium_entrepreneur"} and "spicy" in flavors and random.random() < 0.6:
        flavors = ["savory", "mild"]
    return {
        "preferred_cuisines": preferred,
        "avoided_categories": list(dict.fromkeys(avoided)),
        "portion_preference": portion,
        "flavor_preferences": flavors,
    }


def pick_behavior_habits(latent: Dict[str, float], transport: Dict[str, object]) -> Dict[str, object]:
    wait = int(clamp(random.gauss(24 - latent["delivery_affinity"] * 6, 7), 10, 55))
    return {
        "routine_vs_novelty": latent["routine_mode"],
        "wait_tolerance_minutes": wait,
        "group_ordering_tendency": weighted_choice([("low", 0.25), ("medium", 0.5), ("high", 0.25)]) if transport["main_transport"] != "walk" else weighted_choice([("low", 0.35), ("medium", 0.5), ("high", 0.15)]),
    }


def align_diet_and_restrictions(
    diet_profile: str,
    health_restrictions: Dict[str, bool],
    food_preferences: Dict[str, object],
    food_allergies: Dict[str, bool],
) -> Tuple[str, Dict[str, bool], Dict[str, object]]:
    diet = diet_profile
    hr = dict(health_restrictions)
    prefs = dict(food_preferences)

    # Health-driven soft correction from fast-food bias.
    if (hr.get("low_sugar") or hr.get("low_salt") or hr.get("no_lactose")) and diet == "fast_food":
        if random.random() < 0.45:
            diet = weighted_choice([("healthy_lifestyle", 0.7), ("high_protein", 0.3)])

    # Allergy consistency cues.
    if food_allergies.get("lactose"):
        hr["no_lactose"] = True
    if food_allergies.get("gluten") and random.random() < 0.35:
        if "avoided_categories" in prefs:
            prefs["avoided_categories"] = list(dict.fromkeys(list(prefs["avoided_categories"]) + ["gluten_heavy"]))

    # Vegan/halal soft coherence.
    if diet == "vegan":
        if random.random() < 0.7:
            hr["no_pork"] = False
        if "avoided_categories" in prefs:
            prefs["avoided_categories"] = list(dict.fromkeys(list(prefs["avoided_categories"]) + ["bbq"]))
    if diet == "halal":
        hr["no_pork"] = True

    return diet, hr, prefs


def repair_user(user: Dict) -> Dict:
    u = user
    roles = u["lifestyle_roles"]
    emp = u["employment"]
    if emp["status"] in {"unemployed", "retired"}:
        u["work_location_type"] = "none"
    if emp["status"] == "student" and "university_student" in roles:
        u["work_location_type"] = "university"
    if "factory_worker" in roles:
        u["employment"]["remote_share"] = 0.0
    if u["social_context"]["occasion"] == "business_lunch":
        u["preferred_daypart"] = "lunch"
    return u


def recompute_after_repair(user: Dict) -> Dict:
    u = user
    ch = u["channel_preferences"]
    ch["prefers_delivery"] = ch["primary_order_channel"] in {"delivery_app", "direct_app"}
    sc = u["social_context"]
    if sc["occasion"] == "business_lunch":
        u["preferred_daypart"] = "lunch"
    elif sc["company"] == "family_dinner":
        u["preferred_daypart"] = weighted_choice([("dinner", 0.88), ("lunch", 0.10), ("breakfast", 0.02)])
    elif sc["occasion"] == "quick_snack" and u["preferred_daypart"] == "dinner":
        u["preferred_daypart"] = weighted_choice([("lunch", 0.6), ("breakfast", 0.4)])
    return u


def validate_user(user: Dict) -> Tuple[List[str], List[str]]:
    hard: List[str] = []
    soft: List[str] = []
    sc = user["social_context"]
    roles = set(user["lifestyle_roles"])
    work = user["work_location_type"]
    emp = user["employment"]
    diet = user["diet_profile"]
    cuisines = set(user["food_preferences"]["preferred_cuisines"])
    allergies = user["food_allergies"]
    restrictions = user["health_restrictions"]

    if sc["company"] == "family_dinner" and sc["occasion"] in {"business_lunch", "meeting_place"}:
        hard.append("family_dinner_invalid_occasion")
    if "factory_worker" in roles and work in {"office", "it_office", "remote"}:
        hard.append("factory_wrong_work_location")
    if "office_worker" in roles and work in {"manufacturing_site", "logistics_hub"}:
        hard.append("office_wrong_work_location")
    if "entrepreneur" in roles and work in {"manufacturing_site", "logistics_hub"}:
        hard.append("entrepreneur_wrong_work_location")
    if "it_boy" in roles and work not in {"it_office", "remote", "office"}:
        hard.append("it_boy_wrong_work_location")
    if "school_student" in roles and work not in {"school", "university"}:
        hard.append("school_student_wrong_work_location")
    if "university_student" in roles and work not in {"university", "part_time_job", "retail_store"}:
        hard.append("university_student_wrong_work_location")
    if diet == "vegan" and "bbq" in cuisines:
        hard.append("vegan_with_bbq")
    if diet == "halal" and not restrictions.get("no_pork", False):
        hard.append("halal_without_no_pork")
    if allergies.get("lactose") and not restrictions.get("no_lactose", False):
        hard.append("lactose_without_no_lactose")
    if emp["status"] in {"unemployed", "retired"} and work != "none":
        hard.append("inactive_with_work_location")
    if emp["status"] == "student" and emp["remote_share"] > 0.1:
        hard.append("student_high_remote")
    if "entrepreneur" in roles and emp["status"] != "self_employed":
        hard.append("entrepreneur_not_self_employed")
    if "factory_worker" in roles and emp["remote_share"] > 0:
        hard.append("factory_with_remote_share")
    if "maternity_mom" in roles and (user["sex"] != "female" or not user["household"]["has_infant_child"]):
        hard.append("invalid_maternity_role")
    if "large_family" in roles and user["household"]["children_count"] < 2 and user["household"]["household_size"] < 5:
        hard.append("invalid_large_family_role")
    if user["household"]["household_size"] == 1 and sc["company"] == "family_dinner":
        hard.append("single_household_family_dinner")

    if sc["occasion"] == "quick_snack" and user["preferred_daypart"] == "dinner":
        soft.append("quick_snack_dinner")
    if user["channel_preferences"]["digital_intensity"] == "high" and user["channel_preferences"]["primary_order_channel"] == "in_store" and not user["channel_preferences"]["prefers_delivery"]:
        soft.append("high_digital_instore_no_delivery")
    if diet == "healthy_lifestyle" and cuisines.issubset({"burgers", "pizza", "street_food"}):
        soft.append("healthy_with_only_fastfood_cuisines")
    return hard, soft


def archetype_coherence_score(user: Dict) -> Tuple[float, List[str]]:
    score = 1.0
    issues: List[str] = []
    archetype = user.get("archetype", "unknown")
    role = user.get("lifestyle_roles", ["unknown"])[0]
    work = user.get("work_location_type", "none")
    digital = user.get("channel_preferences", {}).get("digital_intensity", "medium")
    emp = user.get("employment", {})
    hh = user.get("household", {})
    diet = user.get("diet_profile", "fast_food")
    cuisines = set(user.get("food_preferences", {}).get("preferred_cuisines", []))

    if role not in ARCHETYPE_ALLOWED_ROLES.get(archetype, {role}):
        score -= 0.33
        issues.append("archetype_role_mismatch")
    if work not in ARCHETYPE_ALLOWED_WORK.get(archetype, {work}):
        score -= 0.22
        issues.append("archetype_work_mismatch")
    if digital not in ARCHETYPE_EXPECTED_DIGITAL.get(archetype, {"medium"}):
        score -= 0.15
        issues.append("archetype_digital_mismatch")

    if archetype == "premium_entrepreneur" and emp.get("status") != "self_employed":
        score -= 0.18
        issues.append("premium_not_self_employed")
    if archetype == "mature_conservative_factory" and emp.get("remote_share", 0.0) > 0.2:
        score -= 0.15
        issues.append("mature_factory_high_remote")
    if archetype == "young_digital_office" and role == "factory_worker":
        score -= 0.20
        issues.append("young_digital_with_factory_role")
    if archetype == "health_oriented_parent" and diet == "fast_food":
        score -= 0.12
        issues.append("health_parent_fast_food")
    if archetype == "health_oriented_parent" and cuisines and cuisines.issubset({"burgers", "pizza", "street_food"}):
        score -= 0.12
        issues.append("health_parent_only_fastfood_cuisine")
    if archetype in {"family_pragmatic_worker", "health_oriented_parent"} and hh.get("household_size", 1) <= 1:
        score -= 0.08
        issues.append("family_archetype_single_household")
    if archetype == "student_experimenter" and user.get("monthly_income_rub", 0) > 110000:
        score -= 0.12
        issues.append("student_archetype_very_high_income")

    return clamp(score, 0.0, 1.0), issues


def generate_user(district_obj: Dict, idx: int, min_age: int, max_age: int) -> Dict:
    male_pct = float(district_obj["demography"]["sex"]["male_pct"])
    sex = "male" if random.random() < male_pct / 100.0 else "female"
    age = pick_age(district_obj["demography"]["age"], min_age, max_age)
    district_income = pick_income(
        int(district_obj["demography"]["income"]["avg_monthly_personal_income_rub_est"]),
        district_obj["demography"]["income"].get("price_sensitivity", "medium"),
    )
    archetype = pick_archetype(age, district_income, district_obj["district"])
    latent = build_latent(archetype, district_obj["district"])
    education = infer_education(age)
    family = infer_family(age, sex, archetype)
    role_data = lifestyle_roles(district_obj["lifestyle"], sex, age, archetype, family)
    primary_role = role_data["primary_role"]
    secondary_roles = role_data["secondary_roles"]
    roles = [primary_role] + secondary_roles
    life_stage = infer_life_stage(age, family, roles)
    employment = infer_employment(age, primary_role, life_stage)
    income = adjust_income_with_factors(district_income, age, roles, employment, education)

    home_location_type = pick_home_location(district_obj["location"]["home"])
    work_location_type = pick_work_location(
        district_obj["location"]["work"],
        age,
        primary_role,
        employment["status"],
        archetype,
        district_obj["district"],
    )
    employment, work_location_type = normalize_employment_and_work(employment, work_location_type, primary_role, age)
    income_band = income_band_from_value(income)

    health_propensity = clamp(0.35 + latent["health_orientation"] * 0.6, 0.05, 0.98)
    food_allergies = pick_food_allergies(age)
    diet_profile = pick_diet(district_obj["diet_profile"], latent, health_propensity)
    health_restrictions = pick_health_restrictions(food_allergies, age, income)
    transport = pick_transport_and_commute(age, income, district_obj["district"])
    channels = pick_channels(age, income, life_stage, latent, transport, family, district_obj["district"])
    social_context = pick_social_context(
        district_obj["social_context"], age, family, employment["status"], primary_role, latent
    )
    psychographics = pick_psychographics(age, income, life_stage, latent)
    food_preferences = pick_food_preferences_by_archetype(
        archetype, diet_profile, psychographics, latent, district_obj["district"]
    )
    behavior_habits = pick_behavior_habits(latent, transport)
    diet_profile, health_restrictions, food_preferences = align_diet_and_restrictions(
        diet_profile, health_restrictions, food_preferences, food_allergies
    )
    meal_behavior = pick_meal_behavior(
        age,
        income,
        family,
        social_context,
        channels,
        psychographics,
        life_stage,
        diet_profile,
        district_obj["district"],
        archetype,
        food_preferences,
        behavior_habits,
    )
    body = sample_height_weight(sex, age)
    preferred_daypart = pick_daypart(district_obj["daypart"])
    if social_context["occasion"] == "business_lunch":
        preferred_daypart = weighted_choice([("lunch", 0.88), ("breakfast", 0.10), ("dinner", 0.02)])
    elif social_context["company"] == "family_dinner":
        preferred_daypart = weighted_choice([("dinner", 0.86), ("lunch", 0.12), ("breakfast", 0.02)])
    elif social_context["occasion"] == "quick_snack":
        preferred_daypart = weighted_choice([("lunch", 0.55), ("breakfast", 0.33), ("dinner", 0.12)])

    user = {
        "user_id": f"{district_obj['district']}_{idx}",
        "district": district_obj["district"],
        "archetype": archetype,
        "sex": sex,
        "age": age,
        "life_stage": life_stage,
        "education_level": education,
        "monthly_income_rub": income,
        "income_band": income_band,
        "home_location_type": home_location_type,
        "work_location_type": work_location_type,
        "employment": employment,
        "household": family,
        "physical_profile": body,
        "transport": transport,
        "lifestyle_roles": roles,
        "psychographics": psychographics,
        "food_allergies": food_allergies,
        "health_restrictions": health_restrictions,
        "diet_profile": diet_profile,
        "social_context": social_context,
        "preferred_daypart": preferred_daypart,
        "channel_preferences": channels,
        "meal_behavior": meal_behavior,
        "food_preferences": food_preferences,
        "behavior_habits": behavior_habits,
    }
    user = repair_user(user)
    return recompute_after_repair(user)


def generate_valid_user(
    district_obj: Dict, idx: int, min_age: int, max_age: int, max_retries: int = 5
) -> Tuple[Dict, List[str], List[str], bool]:
    last_hard: List[str] = []
    last_soft: List[str] = []
    candidate: Dict = {}
    best_candidate: Dict = {}
    best_hard: List[str] = []
    best_soft: List[str] = []
    best_score = -1.0
    coherence_threshold = 0.58
    for _ in range(max_retries):
        candidate = generate_user(district_obj, idx, min_age, max_age)
        hard, soft = validate_user(candidate)
        coh, coh_issues = archetype_coherence_score(candidate)
        if coh_issues:
            soft = list(soft) + [f"coherence::{issue}" for issue in coh_issues]
        quality = coh - (0.5 if hard else 0.0)
        if quality > best_score:
            best_score = quality
            best_candidate = candidate
            best_hard = hard
            best_soft = soft
        if not hard and coh >= coherence_threshold:
            return candidate, hard, soft, False
        last_hard = hard
        last_soft = soft
    if best_candidate:
        return best_candidate, best_hard, best_soft, True
    return candidate, last_hard, last_soft, True


def compute_qc_for_file(path: Path) -> Dict[str, object]:
    rows = 0
    anomalies = {
        "unemployed_with_work_location": 0,
        "factory_with_remote_share": 0,
        "single_with_family_dinner": 0,
        "student_with_business_lunch": 0,
        "high_digital_phone_order": 0,
        "delivery_app_without_prefers_delivery": 0,
        "student_high_income": 0,
        "retired_too_young": 0,
        "entrepreneur_not_self_employed": 0,
        "it_boy_wrong_work_location": 0,
        "family_dinner_invalid_occasion": 0,
        "factory_wrong_work_location": 0,
        "office_wrong_work_location": 0,
        "vegan_with_bbq": 0,
        "low_archetype_coherence": 0,
    }
    dist = {
        "archetype": {},
        "primary_role": {},
        "channel": {},
        "life_stage": {},
    }
    sum_check = 0.0
    cnt_check = 0
    by_income_band = {"low": [0, 0], "middle": [0, 0], "upper_middle": [0, 0], "high": [0, 0]}
    soft_suspicion_sum = 0.0
    soft_suspicion_count = 0
    soft_suspicion_examples = 0
    coherence_sum = 0.0
    coherence_low = 0
    for line in path.open("r", encoding="utf-8"):
        rows += 1
        o = json.loads(line)
        arch = o.get("archetype", "unknown")
        dist["archetype"][arch] = dist["archetype"].get(arch, 0) + 1
        role = o.get("lifestyle_roles", ["unknown"])[0]
        dist["primary_role"][role] = dist["primary_role"].get(role, 0) + 1
        ch = o["channel_preferences"]["primary_order_channel"]
        dist["channel"][ch] = dist["channel"].get(ch, 0) + 1
        ls = o.get("life_stage", "unknown")
        dist["life_stage"][ls] = dist["life_stage"].get(ls, 0) + 1
        avg_check = o.get("meal_behavior", {}).get("avg_order_check_rub")
        if isinstance(avg_check, (int, float)):
            sum_check += avg_check
            cnt_check += 1
        band = o.get("income_band", "middle")
        if band in by_income_band and isinstance(avg_check, (int, float)):
            by_income_band[band][0] += avg_check
            by_income_band[band][1] += 1
        if o["employment"]["status"] in {"unemployed", "retired"} and o["work_location_type"] != "none":
            anomalies["unemployed_with_work_location"] += 1
        if "factory_worker" in o["lifestyle_roles"] and o["employment"]["remote_share"] > 0:
            anomalies["factory_with_remote_share"] += 1
        if (
            o["social_context"]["company"] == "family_dinner"
            and o["household"]["household_size"] == 1
            and o["household"]["children_count"] == 0
        ):
            anomalies["single_with_family_dinner"] += 1
        if o["employment"]["status"] == "student" and o["social_context"]["occasion"] == "business_lunch":
            anomalies["student_with_business_lunch"] += 1
        if (
            o["channel_preferences"]["digital_intensity"] == "high"
            and o["channel_preferences"]["primary_order_channel"] == "phone_order"
        ):
            anomalies["high_digital_phone_order"] += 1
        if (
            o["channel_preferences"]["primary_order_channel"] == "delivery_app"
            and not o["channel_preferences"]["prefers_delivery"]
        ):
            anomalies["delivery_app_without_prefers_delivery"] += 1
        if o["employment"]["status"] == "student" and o["monthly_income_rub"] > 95000:
            anomalies["student_high_income"] += 1
        if o["employment"]["status"] == "retired" and o["age"] < 55:
            anomalies["retired_too_young"] += 1
        if o["employment"]["status"] != "self_employed" and "entrepreneur" in o["lifestyle_roles"]:
            anomalies["entrepreneur_not_self_employed"] += 1
        if "it_boy" in o["lifestyle_roles"] and o["work_location_type"] not in {"it_office", "remote", "office"}:
            anomalies["it_boy_wrong_work_location"] += 1
        if o["social_context"]["company"] == "family_dinner" and o["social_context"]["occasion"] in {"business_lunch", "meeting_place"}:
            anomalies["family_dinner_invalid_occasion"] += 1
        if "factory_worker" in o["lifestyle_roles"] and o["work_location_type"] not in {"manufacturing_site", "logistics_hub", "service_sector", "retail_store"}:
            anomalies["factory_wrong_work_location"] += 1
        if "office_worker" in o["lifestyle_roles"] and o["work_location_type"] in {"manufacturing_site", "logistics_hub"}:
            anomalies["office_wrong_work_location"] += 1
        if o["diet_profile"] == "vegan" and "bbq" in o["food_preferences"]["preferred_cuisines"]:
            anomalies["vegan_with_bbq"] += 1
        coh, _coh_issues = archetype_coherence_score(o)
        coherence_sum += coh
        if coh < 0.58:
            anomalies["low_archetype_coherence"] += 1
            coherence_low += 1
        # Soft suspicion score (non-binary oddities)
        s = 0.0
        if o["social_context"]["company"] == "family_dinner" and o["household"]["household_size"] == 1:
            s += 1.0
        if o["employment"]["status"] == "student" and o["social_context"]["company"] == "business_meeting":
            s += 2.0
        if o["life_stage"] in {"youth", "student"} and o["meal_behavior"]["new_menu_openness"] == "low":
            s += 1.0
        if o["psychographics"]["price_sensitivity"] in {"high", "medium_to_high"} and o["meal_behavior"]["coupon_sensitivity"] == "low":
            s += 1.0
        if (
            o["health_restrictions"].get("low_sugar")
            and o["health_restrictions"].get("low_salt")
            and o["diet_profile"] == "fast_food"
        ):
            s += 1.5
        if (
            o["channel_preferences"]["digital_intensity"] == "high"
            and o["channel_preferences"]["primary_order_channel"] == "in_store"
            and o["channel_preferences"]["prefers_delivery"] is False
        ):
            s += 0.5
        soft_suspicion_sum += s
        soft_suspicion_count += 1
        if s >= 1.0:
            soft_suspicion_examples += 1
    rates = {k: round((v / rows) * 100, 4) if rows else 0.0 for k, v in anomalies.items()}
    dist_pct = {
        key: {k: round(v / rows * 100, 3) for k, v in sorted(counter.items(), key=lambda x: -x[1])}
        for key, counter in dist.items()
    }
    check_by_band = {}
    for band, (s, c) in by_income_band.items():
        check_by_band[band] = round(s / c, 2) if c else 0.0
    return {
        "rows": rows,
        "anomalies_count": anomalies,
        "anomalies_rate_pct": rates,
        "distribution_pct": dist_pct,
        "avg_order_check_rub": round(sum_check / cnt_check, 2) if cnt_check else 0.0,
        "avg_order_check_by_income_band": check_by_band,
        "soft_suspicion_score_avg": round(soft_suspicion_sum / soft_suspicion_count, 4) if soft_suspicion_count else 0.0,
        "soft_suspicion_examples_rate_pct": round(soft_suspicion_examples / rows * 100, 4) if rows else 0.0,
        "archetype_coherence_score_avg": round(coherence_sum / rows, 4) if rows else 0.0,
        "low_archetype_coherence_rate_pct": round(coherence_low / rows * 100, 4) if rows else 0.0,
    }


def generate_for_district(
    district_obj: Dict, n_users: int, min_age: int, max_age: int
) -> List[Dict]:
    users: List[Dict] = []
    for i in range(1, n_users + 1):
        user, _hard, _soft, _failed = generate_valid_user(
            district_obj, i, min_age, max_age, max_retries=5
        )
        users.append(user)
    return users


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic users from district profile JSON.")
    parser.add_argument(
        "--profile",
        default="krasnoyarsk_districts_profile.json",
        help="Path to district profile JSON file.",
    )
    parser.add_argument(
        "--users-per-district",
        type=int,
        default=10000,
        help="How many users to generate for each district.",
    )
    parser.add_argument(
        "--output",
        default="users.json",
        help="Output JSON file path (no directories are auto-created).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible generation.",
    )
    parser.add_argument(
        "--min-age",
        type=int,
        default=18,
        help="Minimum generated age.",
    )
    parser.add_argument(
        "--max-age",
        type=int,
        default=65,
        help="Maximum generated age.",
    )
    args = parser.parse_args()
    if args.min_age >= args.max_age:
        raise ValueError("--min-age must be less than --max-age")

    random.seed(args.seed)

    profile_path = Path(args.profile)

    with profile_path.open("r", encoding="utf-8") as f:
        profile = json.load(f)

    districts = profile.get("districts", [])
    if not districts:
        raise ValueError("No districts found in profile JSON.")

    all_users: List[Dict] = []
    for district_obj in districts:
        district_users = generate_for_district(
            district_obj,
            args.users_per_district,
            args.min_age,
            args.max_age,
        )
        all_users.extend(district_users)

    combined_path = Path(args.output)
    with combined_path.open("w", encoding="utf-8") as f:
        json.dump(all_users, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
