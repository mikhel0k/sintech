import argparse
import copy
import json
import statistics
from pathlib import Path
from typing import Any, Dict, List, Tuple

from demand_model import DEFAULT_WEIGHTS, evaluate_orders
from jsonutil import load_json


def save_json(path: Path, payload: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def top_items(item_counts: Dict[str, int], menu_items: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
    by_index = {str(item.get("index")): item for item in menu_items}
    result = []
    for item_idx, count in list(item_counts.items())[:top_n]:
        item = by_index.get(item_idx, {})
        result.append(
            {
                "index": int(item_idx),
                "name": item.get("name", f"item_{item_idx}"),
                "count": count,
            }
        )
    return result


def run_case(users: List[Dict[str, Any]], menu_items: List[Dict[str, Any]], seed: int) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    return evaluate_orders(users=users, menu_items=menu_items, seed=seed)


def run_case_with_weights(
    users: List[Dict[str, Any]],
    menu_items: List[Dict[str, Any]],
    seed: int,
    weights: Dict[str, float],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    return evaluate_orders(users=users, menu_items=menu_items, seed=seed, weights=weights)


def scenario_price_up(menu_items: List[Dict[str, Any]], item_index: int, delta_rub: float) -> List[Dict[str, Any]]:
    changed = copy.deepcopy(menu_items)
    for item in changed:
        if item.get("index") == item_index:
            item["price_rub"] = round(float(item.get("price_rub", 0.0)) + delta_rub, 2)
            break
    return changed


def scenario_remove_item(menu_items: List[Dict[str, Any]], item_index: int) -> List[Dict[str, Any]]:
    return [copy.deepcopy(item) for item in menu_items if item.get("index") != item_index]


def scenario_add_item(menu_items: List[Dict[str, Any]], item_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    changed = [copy.deepcopy(item) for item in menu_items]
    changed.append(copy.deepcopy(item_payload))
    return changed


def compare_kpi(base: Dict[str, Any], other: Dict[str, Any]) -> Dict[str, Any]:
    base_rev = float(base.get("total_revenue_rub", 0.0))
    base_avg = float(base.get("avg_check_rub", 0.0))
    new_rev = float(other.get("total_revenue_rub", 0.0))
    new_avg = float(other.get("avg_check_rub", 0.0))
    return {
        "delta_revenue_rub": round(new_rev - base_rev, 2),
        "delta_revenue_pct": round(((new_rev - base_rev) / base_rev) * 100, 3) if base_rev else 0.0,
        "delta_avg_check_rub": round(new_avg - base_avg, 2),
    }


def load_weights(weights_path: Path) -> Dict[str, float]:
    if not weights_path.exists():
        return dict(DEFAULT_WEIGHTS)
    payload = load_json(weights_path)
    if not isinstance(payload, dict):
        raise ValueError("Файл весов должен быть JSON-объектом.")
    inner = payload.get("weights")
    if isinstance(inner, dict):
        payload = inner
    active = dict(DEFAULT_WEIGHTS)
    for key, value in payload.items():
        if isinstance(value, (int, float)):
            active[key] = float(value)
    return active


def find_item(menu_items: List[Dict[str, Any]], item_index: int) -> Dict[str, Any]:
    for item in menu_items:
        if int(item.get("index", -1)) == int(item_index):
            return item
    return {}


def compute_price_elasticity(
    base_kpi: Dict[str, Any],
    scenario_kpi: Dict[str, Any],
    base_menu: List[Dict[str, Any]],
    scenario_menu: List[Dict[str, Any]],
    item_index: int,
) -> Dict[str, Any]:
    key = str(item_index)
    base_demand = float(base_kpi.get("item_counts", {}).get(key, 0))
    new_demand = float(scenario_kpi.get("item_counts", {}).get(key, 0))

    base_item = find_item(base_menu, item_index)
    new_item = find_item(scenario_menu, item_index)
    base_price = float(base_item.get("price_rub", 0.0) or 0.0)
    new_price = float(new_item.get("price_rub", 0.0) or 0.0)

    if base_demand <= 0 or base_price <= 0 or new_price == base_price:
        return {
            "item_index": item_index,
            "base_price": base_price,
            "new_price": new_price,
            "base_demand": base_demand,
            "new_demand": new_demand,
            "elasticity": None,
        }

    demand_change = (new_demand - base_demand) / base_demand
    price_change = (new_price - base_price) / base_price
    elasticity = demand_change / price_change if price_change else None

    return {
        "item_index": item_index,
        "base_price": base_price,
        "new_price": new_price,
        "base_demand": base_demand,
        "new_demand": new_demand,
        "elasticity": round(elasticity, 4) if elasticity is not None else None,
    }


def cannibalization_report(
    base_counts: Dict[str, int],
    new_counts: Dict[str, int],
    menu_items: List[Dict[str, Any]],
    top_n: int = 7,
) -> Dict[str, List[Dict[str, Any]]]:
    all_keys = set(base_counts.keys()) | set(new_counts.keys())
    by_index = {str(item.get("index")): item for item in menu_items}
    deltas = []
    for key in all_keys:
        delta = int(new_counts.get(key, 0)) - int(base_counts.get(key, 0))
        if delta == 0:
            continue
        item = by_index.get(key, {})
        deltas.append(
            {
                "index": int(key),
                "name": item.get("name", f"item_{key}"),
                "delta_orders": delta,
            }
        )
    winners = sorted([x for x in deltas if x["delta_orders"] > 0], key=lambda x: -x["delta_orders"])[:top_n]
    losers = sorted([x for x in deltas if x["delta_orders"] < 0], key=lambda x: x["delta_orders"])[:top_n]
    return {"winners": winners, "losers": losers}


def uncertainty_stats(kpis: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not kpis:
        return {}
    revenues = [float(k["total_revenue_rub"]) for k in kpis]
    checks = [float(k["avg_check_rub"]) for k in kpis]
    return {
        "runs": len(kpis),
        "revenue_mean_rub": round(statistics.mean(revenues), 2),
        "revenue_std_rub": round(statistics.pstdev(revenues), 2) if len(revenues) > 1 else 0.0,
        "avg_check_mean_rub": round(statistics.mean(checks), 2),
        "avg_check_std_rub": round(statistics.pstdev(checks), 2) if len(checks) > 1 else 0.0,
    }


def run_uncertainty(
    users: List[Dict[str, Any]],
    menu_items: List[Dict[str, Any]],
    seed: int,
    n_runs: int,
    weights: Dict[str, float],
) -> List[Dict[str, Any]]:
    kpis: List[Dict[str, Any]] = []
    for i in range(n_runs):
        _, kpi = run_case_with_weights(users, menu_items, seed=seed + i * 97, weights=weights)
        kpis.append(kpi)
    return kpis


def probability_revenue_uplift(base_kpis: List[Dict[str, Any]], scenario_kpis: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not base_kpis or not scenario_kpis:
        return {"p_revenue_gt_baseline": None, "paired_runs": 0}
    paired = min(len(base_kpis), len(scenario_kpis))
    wins = 0
    for i in range(paired):
        if float(scenario_kpis[i]["total_revenue_rub"]) > float(base_kpis[i]["total_revenue_rub"]):
            wins += 1
    return {"p_revenue_gt_baseline": round(wins / paired, 4), "paired_runs": paired}


def parse_deltas(raw: str) -> List[float]:
    values: List[float] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        values.append(float(chunk))
    if 0.0 not in values:
        values.append(0.0)
    return sorted(set(values))


def compute_curve_elasticity(points: List[Dict[str, Any]], base_price: float, base_demand: float) -> Dict[str, Any]:
    if not points or base_price <= 0 or base_demand <= 0:
        return {"elasticity_local": None}
    lower = [p for p in points if p["delta_rub"] < 0]
    upper = [p for p in points if p["delta_rub"] > 0]
    if not lower or not upper:
        return {"elasticity_local": None}
    p1 = max(lower, key=lambda x: x["delta_rub"])
    p2 = min(upper, key=lambda x: x["delta_rub"])
    q1, q2 = float(p1["demand"]), float(p2["demand"])
    pr1, pr2 = float(p1["price_rub"]), float(p2["price_rub"])
    if pr1 == pr2 or (q1 + q2) == 0:
        return {"elasticity_local": None}
    # Arc elasticity around baseline neighborhood.
    elasticity = ((q2 - q1) / ((q1 + q2) / 2.0)) / ((pr2 - pr1) / ((pr1 + pr2) / 2.0))
    return {"elasticity_local": round(elasticity, 4)}


def price_demand_curve(
    users: List[Dict[str, Any]],
    menu_items: List[Dict[str, Any]],
    item_index: int,
    deltas: List[float],
    seed: int,
    weights: Dict[str, float],
) -> Dict[str, Any]:
    base_item = find_item(menu_items, item_index)
    base_price = float(base_item.get("price_rub", 0.0) or 0.0)
    points: List[Dict[str, Any]] = []
    for i, delta in enumerate(deltas):
        scenario_menu = scenario_price_up(menu_items, item_index=item_index, delta_rub=delta)
        _, kpi = run_case_with_weights(users, scenario_menu, seed=seed + 500 + i, weights=weights)
        demand = int(kpi.get("item_counts", {}).get(str(item_index), 0))
        points.append(
            {
                "delta_rub": delta,
                "price_rub": round(base_price + delta, 2),
                "demand": demand,
            }
        )
    base_demand = 0.0
    for p in points:
        if p["delta_rub"] == 0:
            base_demand = float(p["demand"])
            break
    out = {
        "item_index": item_index,
        "base_price": base_price,
        "points": points,
    }
    out.update(compute_curve_elasticity(points, base_price, base_demand))
    return out


def load_menu_items(food_payload: Any) -> List[Dict[str, Any]]:
    if isinstance(food_payload, dict) and "menu_items" in food_payload:
        return food_payload["menu_items"]
    if isinstance(food_payload, list):
        return food_payload
    raise ValueError("food.json должен быть либо массивом, либо объектом с ключом 'menu_items'.")


def main() -> None:
    parser = argparse.ArgumentParser(description="MVP симулятор спроса: baseline + сценарии + отчёт.")
    parser.add_argument("--users", default="users.json", help="Путь к users.json")
    parser.add_argument("--food", default="food.json", help="Путь к food.json")
    parser.add_argument("--report", default="demand_report.json", help="Куда сохранить итоговый отчёт")
    parser.add_argument("--orders-out", default="orders_baseline.jsonl", help="Куда сохранить baseline заказы (JSONL)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--weights",
        default="calibration.json",
        help="JSON с весами: плоский объект чисел или {'weights': {...}} из calibrate.py",
    )
    parser.add_argument("--n-runs", type=int, default=50, help="Число прогонов для оценки неопределенности")
    parser.add_argument("--limit-users", type=int, default=0, help="Обработать только первых N пользователей (0 = все)")
    parser.add_argument(
        "--price-item-index",
        type=int,
        default=4,
        help="Индекс позиции для сценария изменения цены (по умолчанию: хит — курица в медовом соусе)",
    )
    parser.add_argument(
        "--price-delta-rub",
        type=float,
        default=-55.0,
        help="Изменение цены в ₽ (отрицательное = промо/скидка на позицию)",
    )
    parser.add_argument(
        "--elasticity-deltas",
        default="-100,-50,0,50,100",
        help="Список дельт цены через запятую для price-demand кривой (например -100,-50,0,50,100)",
    )
    parser.add_argument(
        "--remove-item-index",
        type=int,
        default=19,
        help="Индекс позиции для сценария удаления из меню (по умолчанию: фокачча как типичный гарнир)",
    )
    parser.add_argument(
        "--new-item-json",
        default="",
        help="Путь к JSON файлу нового блюда для сценария add_item (если пусто, используется встроенное блюдо)",
    )
    args = parser.parse_args()

    users_payload = load_json(
        Path(args.users),
        hint="Сгенерируйте пользователей, например:\n"
        "  python create_users.py --users-per-district 500 --output users.json",
    )
    food_payload = load_json(
        Path(args.food),
        hint="Сгенерируйте меню:\n  python create_food.py",
    )

    if not isinstance(users_payload, list):
        raise ValueError("users.json должен быть JSON-массивом пользователей.")
    users = users_payload[: args.limit_users] if args.limit_users > 0 else users_payload
    if not users:
        raise ValueError("Список пользователей пуст.")

    menu_items = load_menu_items(food_payload)
    if not menu_items:
        raise ValueError("Список блюд пуст.")
    weights = load_weights(Path(args.weights))

    # Baseline
    print("Running baseline...")
    baseline_orders, baseline_kpi = run_case_with_weights(users, menu_items, seed=args.seed, weights=weights)

    with Path(args.orders_out).open("w", encoding="utf-8") as f:
        for row in baseline_orders:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # Scenario 1: +price
    print("Running scenario: price_up...")
    menu_price = scenario_price_up(menu_items, item_index=args.price_item_index, delta_rub=args.price_delta_rub)
    _, kpi_price = run_case_with_weights(users, menu_price, seed=args.seed + 1, weights=weights)

    # Scenario 2: remove item
    print("Running scenario: remove_item...")
    menu_remove = scenario_remove_item(menu_items, item_index=args.remove_item_index)
    _, kpi_remove = run_case_with_weights(users, menu_remove, seed=args.seed + 2, weights=weights)

    # Scenario 3: add item
    if args.new_item_json:
        add_item_payload = load_json(Path(args.new_item_json))
    else:
        max_idx = max(int(item.get("index", 0)) for item in menu_items)
        add_item_payload = {
            "index": max_idx + 1,
            "name": "Боул с печёной индейкой, булгуром и йогуртовым соусом",
            "price_rub": 535,
            "calories": 605,
            "protein_g": 40,
            "carbs_g": 52,
            "fat_g": 22,
            "sugar_g": 5,
            "category": "bowl",
            "tags": ["chicken", "bowl", "balanced", "healthy", "high_protein", "fresh"],
            "taste": ["umami", "fresh"],
            "time_fit": ["lunch", "dinner"],
        }
    menu_add = scenario_add_item(menu_items, add_item_payload)
    print("Running scenario: add_item...")
    _, kpi_add = run_case_with_weights(users, menu_add, seed=args.seed + 3, weights=weights)

    print(f"Running uncertainty block with n_runs={args.n_runs}...")
    baseline_unc_runs = run_uncertainty(users, menu_items, args.seed + 1000, args.n_runs, weights)
    price_unc_runs = run_uncertainty(users, menu_price, args.seed + 2000, args.n_runs, weights)
    remove_unc_runs = run_uncertainty(users, menu_remove, args.seed + 3000, args.n_runs, weights)
    add_unc_runs = run_uncertainty(users, menu_add, args.seed + 4000, args.n_runs, weights)
    elasticity_curve = price_demand_curve(
        users=users,
        menu_items=menu_items,
        item_index=args.price_item_index,
        deltas=parse_deltas(args.elasticity_deltas),
        seed=args.seed,
        weights=weights,
    )

    report = {
        "meta": {
            "users_path": args.users,
            "food_path": args.food,
            "users_count": len(users),
            "seed": args.seed,
            "weights_path": args.weights,
            "n_runs_uncertainty": args.n_runs,
        },
        "baseline": {
            "kpi": baseline_kpi,
            "top_items": top_items(baseline_kpi["item_counts"], menu_items, top_n=7),
            "uncertainty": uncertainty_stats(baseline_unc_runs),
        },
        "scenarios": {
            "price_up": {
                "params": {"item_index": args.price_item_index, "delta_rub": args.price_delta_rub},
                "kpi": kpi_price,
                "delta_vs_baseline": compare_kpi(baseline_kpi, kpi_price),
                "elasticity": compute_price_elasticity(
                    baseline_kpi, kpi_price, menu_items, menu_price, args.price_item_index
                ),
                "cannibalization": cannibalization_report(
                    baseline_kpi["item_counts"], kpi_price["item_counts"], menu_price, top_n=7
                ),
                "top_items": top_items(kpi_price["item_counts"], menu_price, top_n=7),
                "uncertainty": uncertainty_stats(price_unc_runs),
                "probability": probability_revenue_uplift(baseline_unc_runs, price_unc_runs),
                "elasticity_curve": elasticity_curve,
            },
            "remove_item": {
                "params": {"item_index": args.remove_item_index},
                "kpi": kpi_remove,
                "delta_vs_baseline": compare_kpi(baseline_kpi, kpi_remove),
                "cannibalization": cannibalization_report(
                    baseline_kpi["item_counts"], kpi_remove["item_counts"], menu_remove, top_n=7
                ),
                "top_items": top_items(kpi_remove["item_counts"], menu_remove, top_n=7),
                "uncertainty": uncertainty_stats(remove_unc_runs),
                "probability": probability_revenue_uplift(baseline_unc_runs, remove_unc_runs),
            },
            "add_item": {
                "params": {"item": add_item_payload},
                "kpi": kpi_add,
                "delta_vs_baseline": compare_kpi(baseline_kpi, kpi_add),
                "cannibalization": cannibalization_report(
                    baseline_kpi["item_counts"], kpi_add["item_counts"], menu_add, top_n=7
                ),
                "top_items": top_items(kpi_add["item_counts"], menu_add, top_n=7),
                "uncertainty": uncertainty_stats(add_unc_runs),
                "probability": probability_revenue_uplift(baseline_unc_runs, add_unc_runs),
            },
        },
    }

    save_json(Path(args.report), report)
    print(f"Done. Report: {args.report}")
    print(f"Baseline orders: {args.orders_out}")


if __name__ == "__main__":
    main()

