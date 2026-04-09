import argparse
from pathlib import Path
from typing import Any, Dict, List

from calibration_eval import evaluate_weights, load_json, load_menu_items, save_json
from demand_model import DEFAULT_WEIGHTS


def main() -> None:
    parser = argparse.ArgumentParser(description="Калибровка весов модели спроса (Optuna).")
    parser.add_argument("--users", default="users.json")
    parser.add_argument("--food", default="food.json")
    parser.add_argument(
        "--output",
        default="calibration.json",
        help="Один файл: weights + метаданные прогона Optuna (для simulate_demand --weights)",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--limit-users", type=int, default=2000)
    parser.add_argument("--trials", type=int, default=80)
    parser.add_argument("--uncertainty-runs", type=int, default=8)
    parser.add_argument("--elasticity-item-index", type=int, default=5)
    parser.add_argument("--elasticity-delta-rub", type=float, default=50.0)
    parser.add_argument("--avg-check-min", type=float, default=650.0)
    parser.add_argument("--avg-check-max", type=float, default=750.0)
    parser.add_argument("--max-std-revenue", type=float, default=15000.0)
    parser.add_argument("--elasticity-min", type=float, default=-2.5)
    parser.add_argument("--elasticity-max", type=float, default=-0.8)
    parser.add_argument("--max-top-item-share", type=float, default=0.15)
    args = parser.parse_args()

    try:
        import optuna
    except ImportError as exc:
        raise SystemExit(
            "Optuna не установлен. Установи: ./.venv/bin/pip install optuna"
        ) from exc

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
        raise ValueError("users.json должен быть массивом.")
    users: List[Dict[str, Any]] = users_payload[: args.limit_users] if args.limit_users > 0 else users_payload
    menu_items = load_menu_items(food_payload)

    def objective(trial: "optuna.trial.Trial") -> float:
        weights = dict(DEFAULT_WEIGHTS)
        weights["price_base_penalty"] = trial.suggest_float("price_base_penalty", 1.0, 3.5)
        weights["price_sensitivity_multiplier"] = trial.suggest_float("price_sensitivity_multiplier", 1.5, 5.5)
        weights["relative_price_coef"] = trial.suggest_float("relative_price_coef", 0.4, 2.2)
        weights["utility_scale"] = trial.suggest_float("utility_scale", 2.0, 5.0)
        weights["temperature"] = trial.suggest_float("temperature", 1.2, 2.3)
        weights["max_price_impact"] = trial.suggest_float("max_price_impact", 0.3, 0.7)
        weights["noise_sigma"] = trial.suggest_float("noise_sigma", 0.08, 0.24)
        weights["healthy_bonus"] = trial.suggest_float("healthy_bonus", 0.2, 1.0)
        weights["high_protein_bonus"] = trial.suggest_float("high_protein_bonus", 0.2, 1.2)
        weights["preferred_healthy_bonus"] = trial.suggest_float("preferred_healthy_bonus", 0.1, 0.8)
        weights["preferred_american_bonus"] = trial.suggest_float("preferred_american_bonus", 0.05, 0.5)
        weights["vegetarian_meat_penalty"] = -abs(trial.suggest_float("vegetarian_meat_penalty_abs", 0.8, 2.2))
        weights["substitution_overlap_coef"] = -abs(trial.suggest_float("substitution_overlap_coef_abs", 0.05, 0.35))
        weights["taste_match_weight"] = trial.suggest_float("taste_match_weight", 0.15, 0.75)
        weights["time_fit_bonus"] = trial.suggest_float("time_fit_bonus", 0.12, 0.45)
        weights["satiety_weight"] = trial.suggest_float("satiety_weight", 0.05, 0.22)

        ev = evaluate_weights(
            users=users,
            menu_items=menu_items,
            weights=weights,
            seed=args.seed + trial.number * 17,
            elasticity_item_index=args.elasticity_item_index,
            elasticity_delta_rub=args.elasticity_delta_rub,
            avg_check_range=(args.avg_check_min, args.avg_check_max),
            max_std_revenue=args.max_std_revenue,
            uncertainty_runs=args.uncertainty_runs,
            elasticity_range=(args.elasticity_min, args.elasticity_max),
            max_top_item_share=args.max_top_item_share,
        )
        trial.set_user_attr("metrics", ev)
        return float(ev["loss"])

    sampler = optuna.samplers.TPESampler(seed=args.seed)
    study = optuna.create_study(direction="minimize", sampler=sampler)
    study.optimize(objective, n_trials=args.trials)

    best = study.best_trial
    best_weights = dict(DEFAULT_WEIGHTS)
    for k, v in best.params.items():
        if k == "vegetarian_meat_penalty_abs":
            best_weights["vegetarian_meat_penalty"] = -abs(float(v))
        elif k == "substitution_overlap_coef_abs":
            best_weights["substitution_overlap_coef"] = -abs(float(v))
        else:
            best_weights[k] = float(v)

    out_path = Path(args.output)
    save_json(
        out_path,
        {
            "weights": best_weights,
            "calibration": {
                "trials": args.trials,
                "users_used": len(users),
                "seed": args.seed,
                "best_loss": best.value,
                "best_params": best.params,
                "best_metrics": best.user_attrs.get("metrics", {}),
            },
        },
    )
    print(f"Done. {out_path} (weights + calibration meta)")
    print(f"Best loss: {best.value}")


if __name__ == "__main__":
    main()
