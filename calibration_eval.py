"""Оценка loss для подбора весов (используется calibrate.py / Optuna)."""

import json
import statistics
from pathlib import Path
from typing import Any, Dict, List, Tuple

from demand_model import evaluate_orders
from jsonutil import load_json


def save_json(path: Path, payload: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def load_menu_items(food_payload: Any) -> List[Dict[str, Any]]:
    if isinstance(food_payload, dict) and "menu_items" in food_payload:
        return food_payload["menu_items"]
    if isinstance(food_payload, list):
        return food_payload
    raise ValueError("food.json должен быть массивом или объектом с menu_items.")


def scenario_price_up(menu_items: List[Dict[str, Any]], item_index: int, delta_rub: float) -> List[Dict[str, Any]]:
    out = [dict(item) for item in menu_items]
    for item in out:
        if int(item.get("index", -1)) == int(item_index):
            item["price_rub"] = round(float(item.get("price_rub", 0.0)) + float(delta_rub), 2)
            break
    return out


def get_demand(kpi: Dict[str, Any], item_index: int) -> float:
    return float(kpi.get("item_counts", {}).get(str(item_index), 0))


def run_kpi(users: List[Dict[str, Any]], menu_items: List[Dict[str, Any]], seed: int, weights: Dict[str, float]) -> Dict[str, Any]:
    _, kpi = evaluate_orders(users=users, menu_items=menu_items, seed=seed, weights=weights)
    return kpi


def effective_elasticity(
    base_kpi: Dict[str, Any],
    new_kpi: Dict[str, Any],
    base_price: float,
    new_price: float,
    item_index: int,
) -> float:
    base_d = get_demand(base_kpi, item_index)
    new_d = get_demand(new_kpi, item_index)
    if base_d <= 0 or base_price <= 0 or new_price == base_price:
        return 0.0
    d_change = (new_d - base_d) / base_d
    p_change = (new_price - base_price) / base_price
    if p_change == 0:
        return 0.0
    return d_change / p_change


def uncertainty_std_revenue(
    users: List[Dict[str, Any]],
    menu_items: List[Dict[str, Any]],
    base_seed: int,
    n_runs: int,
    weights: Dict[str, float],
) -> float:
    revenues = []
    for i in range(n_runs):
        kpi = run_kpi(users, menu_items, seed=base_seed + i * 97, weights=weights)
        revenues.append(float(kpi["total_revenue_rub"]))
    if len(revenues) <= 1:
        return 0.0
    return float(statistics.pstdev(revenues))


def evaluate_weights(
    users: List[Dict[str, Any]],
    menu_items: List[Dict[str, Any]],
    weights: Dict[str, float],
    seed: int,
    elasticity_item_index: int,
    elasticity_delta_rub: float,
    avg_check_range: Tuple[float, float],
    max_std_revenue: float,
    uncertainty_runs: int,
    elasticity_range: Tuple[float, float],
    max_top_item_share: float,
) -> Dict[str, Any]:
    base_kpi = run_kpi(users, menu_items, seed=seed, weights=weights)
    menu_up = scenario_price_up(menu_items, item_index=elasticity_item_index, delta_rub=elasticity_delta_rub)
    up_kpi = run_kpi(users, menu_up, seed=seed + 1, weights=weights)

    base_item_price = 0.0
    for it in menu_items:
        if int(it.get("index", -1)) == int(elasticity_item_index):
            base_item_price = float(it.get("price_rub", 0.0))
            break
    new_item_price = base_item_price + elasticity_delta_rub

    e_eff = effective_elasticity(
        base_kpi=base_kpi,
        new_kpi=up_kpi,
        base_price=base_item_price,
        new_price=new_item_price,
        item_index=elasticity_item_index,
    )
    std_rev = uncertainty_std_revenue(
        users=users,
        menu_items=menu_items,
        base_seed=seed + 1000,
        n_runs=uncertainty_runs,
        weights=weights,
    )
    avg_check = float(base_kpi["avg_check_rub"])

    low, high = avg_check_range
    e_low, e_high = elasticity_range
    loss = 0.0

    if e_eff > e_high:
        loss += 50.0 + 12.0 * (e_eff - e_high)
    if e_eff < e_low:
        loss += 8.0 * (e_low - e_eff)

    if avg_check < low:
        loss += (low - avg_check) / 40.0
    if avg_check > high:
        loss += (avg_check - high) / 40.0

    if std_rev > max_std_revenue:
        loss += (std_rev - max_std_revenue) / 2500.0

    item_counts = base_kpi.get("item_counts", {})
    total_items = sum(int(v) for v in item_counts.values())
    top_count = max((int(v) for v in item_counts.values()), default=0)
    top_share = (top_count / total_items) if total_items else 0.0
    if top_share > max_top_item_share:
        loss += 15.0 * (top_share - max_top_item_share) * 100.0

    loss += max(0.0, weights["noise_sigma"] - 0.2) * 2.0

    return {
        "loss": round(loss, 6),
        "effective_elasticity": round(e_eff, 4),
        "avg_check_rub": round(avg_check, 2),
        "revenue_std_rub": round(std_rev, 2),
        "top_item_share": round(top_share, 4),
        "base_kpi": base_kpi,
    }
