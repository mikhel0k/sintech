import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple


# Старые отчёты с англ. именами из food.json; новые меню уже с русскими name — тогда ru_name() не меняет строку.
RU_NAME_MAP = {
    "Chicken Sesame Crunch": "Салат с курицей и кунжутом",
    "Caramelized Garlic Steak": "Стейк с карамелизованным чесноком",
    "Miso Glazed Salmon": "Лосось в мисо-глазури",
    "Hot Honey Chicken": "Курица в остро-сладком медовом соусе",
    "Steak Mezze": "Стейк с гарниром мезе",
    "Harvest Bowl": "Боул «Урожай» с курицей и бататом",
    "Crispy Rice Bowl": "Боул с хрустящим рисом и курицей",
    "Chicken Pesto Parm": "Боул с курицей, песто и пармезаном",
    "Chicken Avocado Ranch": "Боул с курицей, авокадо и соусом ранч",
    "Shroomami": "Тёплый веганский боул с грибами",
    "Fish Taco": "Боул с лососем и соусом тако",
    "Steak Honey Crunch": "Боул со стейком и острым мёдом",
    "Kale Caesar": "Салат кейл-цезарь с курицей",
    "Guacamole Greens": "Салат с курицей и гуакамоле",
    "Super Green Goddess": "Зелёный салат «Годдесс»",
    "BBQ Chicken Salad": "Салат с курицей и соусом барбекю",
    "Hummus Crunch": "Салат с хумусом и хрустящим нутом",
    "Buffalo Chicken": "Острый салат «Буффало» с курицей",
    "Rosemary Focaccia": "Фокачча с розмарином",
    "Hummus + Focaccia": "Хумус с фокаччей",
    "Roasted Sweet Potatoes": "Запечённый батат",
    "Crispy Rice Treat": "Десерт из хрустящего риса",
    "HU Cashews + Vanilla Bean Hunks": "Десерт: кешью с ванилью",
    "HU Salty Dark Chocolate Bar": "Плитка тёмного шоколада с солью",
    "Open Water Still Water": "Вода питьевая, негазированная",
    "Open Water Sparkling Water": "Вода минеральная газированная",
    "OLIPOP Lemon Lime Soda": "Газировка лимон-лайм (мало сахара)",
    "OLIPOP Vintage Cola": "Газировка «кола» (мало сахара)",
    "Spindrift Raspberry Lime": "Напиток с малиной и лаймом",
    "Spindrift Grapefruit": "Напиток с грейпфрутом",
    "Jasmine Green Tea": "Зелёный чай с жасмином",
    "Hibiscus Berry Clover Tea": "Холодный чай: гибискус и ягоды",
    "Harney + Sons Organic Lemonade": "Домашний лимонад",
    "Health-Ade Kombucha Pink Lady Apple": "Комбуча с яблоком",
    "Health-Ade Kombucha Passionfruit Tangerine": "Комбуча маракуйя и мандарин",
    "Seasonal Protein Bowl": "Сезонный протеиновый боул",
}


from jsonutil import load_json as load_json_file


def get_menu_items(food_payload: Any) -> List[Dict[str, Any]]:
    if isinstance(food_payload, dict) and "menu_items" in food_payload:
        return food_payload["menu_items"]
    if isinstance(food_payload, list):
        return food_payload
    return []


def fmt_money(v: float) -> str:
    return f"{v:,.0f}".replace(",", " ")


def fmt_signed_rub(v: float) -> str:
    """Человекочитаемая дельта в рублях со знаком (минус — Unicode −)."""
    if v < 0:
        return f"−{fmt_money(abs(v))}"
    if v > 0:
        return f"+{fmt_money(v)}"
    return "0"


def fmt_price_shift_rub(delta_rub: float) -> str:
    """Подпись изменения цены для сценария (в т.ч. промо при отрицательной дельте)."""
    if delta_rub > 0:
        return f"+{fmt_money(delta_rub)} ₽"
    if delta_rub < 0:
        return f"−{fmt_money(abs(delta_rub))} ₽"
    return "0 ₽"


def fmt_pct(v: float) -> str:
    return f"{v:.1f}%"


def ru_name(name: str) -> str:
    return RU_NAME_MAP.get(name, name)


def idx_to_item_map(menu_items: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    out: Dict[int, Dict[str, Any]] = {}
    for item in menu_items:
        idx = item.get("index")
        if isinstance(idx, int):
            out[idx] = item
    return out


def estimate_cost(price_rub: float) -> float:
    return price_rub * 0.45


def short_item_desc(item: Dict[str, Any]) -> str:
    category_ru = {
        "protein_plate": "основное блюдо",
        "bowl": "боул",
        "salad": "салат",
        "side": "гарнир",
        "dessert": "десерт",
        "drink": "напиток",
    }
    c = category_ru.get(str(item.get("category", "")), "позиция")
    price = int(item.get("price_rub", 0) or 0)
    protein = int(item.get("protein_g", 0) or 0)
    kcal = int(item.get("calories", 0) or 0)
    return f"{c}, {price} ₽, {kcal} ккал, белки {protein} г"


def medium_item_desc(item: Dict[str, Any]) -> str:
    category_ru = {
        "protein_plate": "основное блюдо",
        "bowl": "боул",
        "salad": "салат",
        "side": "гарнир/снэк",
        "dessert": "десерт",
        "drink": "напиток",
    }
    c = category_ru.get(str(item.get("category", "")), "позиция")
    price = int(item.get("price_rub", 0) or 0)
    protein = int(item.get("protein_g", 0) or 0)
    kcal = int(item.get("calories", 0) or 0)
    tags = item.get("tags", [])
    tag_text = ", ".join(tags[:4]) if isinstance(tags, list) and tags else "без тегов"
    return f"{c}, {price} ₽, {kcal} ккал, белки {protein} г, теги: {tag_text}"


def top_and_bottom_items(item_counts: Dict[str, int], n: int = 5) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
    pairs = [(int(k), int(v)) for k, v in item_counts.items()]
    top = sorted(pairs, key=lambda x: -x[1])[:n]
    bottom = sorted(pairs, key=lambda x: x[1])[:n]
    return top, bottom


def split_lines(text: str, max_len: int = 90) -> List[str]:
    if not text:
        return [""]
    words = text.split()
    lines: List[str] = []
    current: List[str] = []
    current_len = 0
    for word in words:
        add_len = len(word) + (1 if current else 0)
        if current_len + add_len > max_len:
            lines.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += add_len
    if current:
        lines.append(" ".join(current))
    return lines


def wrap_text_lines(lines: List[str], max_chars: int) -> List[str]:
    wrapped: List[str] = []
    for line in lines:
        if not line:
            wrapped.append("")
            continue
        wrapped.extend(split_lines(line, max_len=max_chars))
    return wrapped


def build_pdf(report: Dict[str, Any], menu_item_map: Dict[int, Dict[str, Any]], output_pdf: Path) -> None:
    try:
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
        from matplotlib import rcParams
        from matplotlib.patches import FancyBboxPatch
        import matplotlib.gridspec as gridspec
    except ImportError as exc:
        raise SystemExit("Не найден matplotlib. Установи: ./.venv/bin/pip install matplotlib") from exc

    rcParams["font.family"] = "DejaVu Sans"
    rcParams["font.size"] = 10
    rcParams["axes.unicode_minus"] = False
    rcParams["axes.facecolor"] = "white"
    rcParams["figure.facecolor"] = "white"

    COLORS = {
        "navy": "#0F172A",
        "blue": "#2563EB",
        "blue_soft": "#EFF6FF",
        "green": "#16A34A",
        "green_soft": "#F0FDF4",
        "red": "#DC2626",
        "red_soft": "#FEF2F2",
        "amber": "#D97706",
        "amber_soft": "#FFF7ED",
        "slate": "#475569",
        "slate_light": "#CBD5E1",
        "panel": "#F8FAFC",
        "white": "#FFFFFF",
    }

    baseline = report["baseline"]["kpi"]
    scenarios = report["scenarios"]

    add_item = scenarios["add_item"]["params"]["item"]
    add_name = ru_name(add_item.get("name", "unknown"))

    remove_idx = int(scenarios["remove_item"]["params"]["item_index"])
    remove_item = menu_item_map.get(remove_idx, {"name": f"item_{remove_idx}"})
    remove_name = ru_name(remove_item.get("name", f"item_{remove_idx}"))

    price_idx = int(scenarios["price_up"]["params"]["item_index"])
    price_item = menu_item_map.get(price_idx, {"name": f"item_{price_idx}"})
    price_name = ru_name(price_item.get("name", f"item_{price_idx}"))

    price_delta_rub = float(scenarios["price_up"]["params"].get("delta_rub", 0))
    price_shift_lbl = fmt_price_shift_rub(price_delta_rub)
    price_scenario_human = (
        f"промо на «{price_name}» ({price_shift_lbl})"
        if price_delta_rub < 0
        else f"повышение цены «{price_name}» ({price_shift_lbl})"
        if price_delta_rub > 0
        else f"цена «{price_name}» без изменений"
    )

    b_rev = float(baseline["total_revenue_rub"])
    b_check = float(baseline["avg_check_rub"])
    b_items = float(baseline["avg_items_per_order"])
    b_std = float(report["baseline"].get("uncertainty", {}).get("revenue_std_rub", 0.0))

    d_add = float(scenarios["add_item"]["delta_vs_baseline"]["delta_revenue_rub"])
    d_remove = float(scenarios["remove_item"]["delta_vs_baseline"]["delta_revenue_rub"])
    d_price = float(scenarios["price_up"]["delta_vs_baseline"]["delta_revenue_rub"])

    p_add = float(scenarios["add_item"]["probability"]["p_revenue_gt_baseline"]) * 100
    p_remove = float(scenarios["remove_item"]["probability"]["p_revenue_gt_baseline"]) * 100
    p_price = float(scenarios["price_up"]["probability"]["p_revenue_gt_baseline"]) * 100

    scenario_ranked = [
        ("Добавление позиции", d_add, p_add),
        (f"Цена {price_shift_lbl} ({price_name})", d_price, p_price),
        ("Удаление из меню", d_remove, p_remove),
    ]
    best_label, best_d, best_p = max(scenario_ranked, key=lambda x: x[1])
    # max() по числу: при всех минусах это «меньшее по модулю» падение, не «рост».
    if best_d > 0:
        kpi_compare_title = "Лучший сценарий"
        kpi_compare_hint = "наибольший прирост к базовой выручке"
    elif best_d < 0:
        kpi_compare_title = "Наименьший спад"
        kpi_compare_hint = "все три сценария хуже базы; здесь урон меньше, чем у двух других"
    else:
        kpi_compare_title = "Сценарии"
        kpi_compare_hint = "суммарная выручка почти как в базе"

    margin_values = []
    for item in menu_item_map.values():
        pr = float(item.get("price_rub", 0))
        cost = estimate_cost(pr)
        margin_values.append((pr - cost) / pr if pr > 0 else 0)
    avg_margin_pct = (sum(margin_values) / len(margin_values) * 100) if margin_values else 0.0

    top_items, bottom_items = top_and_bottom_items(baseline["item_counts"], n=5)

    rev_mean = float(report["baseline"].get("uncertainty", {}).get("revenue_mean_rub", b_rev))
    rev_std = float(report["baseline"].get("uncertainty", {}).get("revenue_std_rub", b_std))
    rev_low = max(0.0, rev_mean - 1.5 * rev_std)
    rev_high = rev_mean + 1.5 * rev_std
    profit_low = rev_low * (avg_margin_pct / 100.0)
    profit_high = rev_high * (avg_margin_pct / 100.0)

    breakeven_orders_day = (b_rev * 0.15 / max(b_check, 1.0)) / 30.0

    stability = max(0.6, 1.0 - (b_std / max(b_rev, 1.0)) * 8.0)
    item_scores = []
    for idx_str, cnt in baseline["item_counts"].items():
        idx = int(idx_str)
        item = menu_item_map.get(idx, {"name": f"item_{idx}", "price_rub": 0})
        pr = float(item.get("price_rub", 0))
        margin = pr - estimate_cost(pr)
        score = float(cnt) * margin * stability
        item_scores.append((idx, float(cnt), margin, score))
    item_scores_sorted = sorted(item_scores, key=lambda x: -x[3])
    keep_items = item_scores_sorted[:3]
    remove_items = sorted(item_scores, key=lambda x: x[3])[:2]
    tune_items = sorted(item_scores, key=lambda x: x[2])[:2]

    def add_footer(fig: Any, page_num: int) -> None:
        fig.text(
            0.5,
            0.015,
            f"Отчёт по спросу и меню · стр. {page_num}",
            ha="center",
            va="bottom",
            fontsize=8,
            color=COLORS["slate"],
        )

    def hide_axis(ax: Any) -> None:
        ax.set_xticks([])
        ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_visible(False)

    def clean_axis(ax: Any) -> None:
        ax.grid(axis="y", color=COLORS["slate_light"], linestyle="--", linewidth=0.6, alpha=0.8)
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(COLORS["slate_light"])
        ax.spines["bottom"].set_color(COLORS["slate_light"])
        ax.tick_params(colors=COLORS["slate"])
        ax.title.set_color(COLORS["navy"])

    def draw_kpi_card(ax: Any, title: str, value: str, subtitle: str, tone: str = "blue") -> None:
        tone_map = {
            "blue": (COLORS["blue_soft"], COLORS["blue"]),
            "green": (COLORS["green_soft"], COLORS["green"]),
            "red": (COLORS["red_soft"], COLORS["red"]),
            "amber": (COLORS["amber_soft"], COLORS["amber"]),
        }
        bg, fg = tone_map[tone]
        hide_axis(ax)
        ax.add_patch(
            FancyBboxPatch(
                (0.02, 0.08),
                0.96,
                0.84,
                boxstyle="round,pad=0.018,rounding_size=14",
                linewidth=1.0,
                edgecolor=COLORS["slate_light"],
                facecolor=bg,
                transform=ax.transAxes,
            )
        )
        ax.text(0.08, 0.78, title, fontsize=10, color=COLORS["slate"], fontweight="bold", transform=ax.transAxes)
        ax.text(0.08, 0.50, value, fontsize=18, color=fg, fontweight="bold", transform=ax.transAxes)
        ax.text(0.08, 0.23, subtitle, fontsize=9, color=COLORS["slate"], transform=ax.transAxes)

    def draw_text_panel(
        ax: Any,
        title: str,
        lines: List[str],
        tone: str = "panel",
        max_chars: int = 70,
        base_fontsize: float = 10.5,
        min_fontsize: float = 9.0,
        line_step: float = 0.078,
    ) -> None:
        tone_map = {
            "panel": (COLORS["panel"], COLORS["slate_light"]),
            "amber": (COLORS["amber_soft"], "#FED7AA"),
            "green": (COLORS["green_soft"], "#BBF7D0"),
            "red": (COLORS["red_soft"], "#FECACA"),
            "blue": (COLORS["blue_soft"], "#BFDBFE"),
        }
        bg, border = tone_map[tone]
        hide_axis(ax)

        ax.add_patch(
            FancyBboxPatch(
                (0.01, 0.03),
                0.98,
                0.94,
                boxstyle="round,pad=0.02,rounding_size=14",
                linewidth=1.0,
                edgecolor=border,
                facecolor=bg,
                transform=ax.transAxes,
            )
        )

        ax.text(
            0.04,
            0.92,
            title,
            fontsize=12,
            color=COLORS["navy"],
            fontweight="bold",
            va="top",
            transform=ax.transAxes,
        )

        wrapped = wrap_text_lines(lines, max_chars=max_chars)

        top_y = 0.84
        bottom_y = 0.08
        available = top_y - bottom_y

        fontsize = base_fontsize
        current_step = line_step

        while fontsize >= min_fontsize:
            needed = len(wrapped) * current_step
            if needed <= available:
                break
            fontsize -= 0.35
            current_step = max(0.062, current_step - 0.0025)

        max_lines = int(available / current_step)
        visible = wrapped[:max_lines]

        if len(wrapped) > max_lines and visible:
            last = visible[-1]
            visible[-1] = (last[: max(0, len(last) - 3)] + "...") if len(last) > 3 else "..."

        y = top_y
        for line in visible:
            ax.text(
                0.05,
                y,
                line,
                fontsize=fontsize,
                color=COLORS["navy"],
                va="top",
                transform=ax.transAxes,
            )
            y -= current_step

    def draw_table(ax: Any, title: str, col_labels: List[str], rows: List[List[str]], font_size: float = 9.0) -> None:
        hide_axis(ax)
        ax.text(
            0.0,
            1.02,
            title,
            fontsize=12,
            fontweight="bold",
            color=COLORS["navy"],
            transform=ax.transAxes,
        )

        table = ax.table(
            cellText=rows,
            colLabels=col_labels,
            loc="upper center",
            cellLoc="left",
            colLoc="left",
            bbox=[0.0, 0.0, 1.0, 0.92],
        )
        table.auto_set_font_size(False)
        table.set_fontsize(font_size)
        table.scale(1, 1.55)

        for (r, c), cell in table.get_celld().items():
            cell.set_edgecolor(COLORS["slate_light"])
            cell.set_linewidth(0.7)
            if r == 0:
                cell.set_facecolor(COLORS["blue_soft"])
                cell.set_text_props(weight="bold", color=COLORS["navy"])
            else:
                cell.set_facecolor(COLORS["white"])

    def bar_colors(values: List[float]) -> List[str]:
        colors = []
        for v in values:
            colors.append(COLORS["green"] if v >= 0 else COLORS["red"])
        return colors

    with PdfPages(output_pdf) as pdf:
        # PAGE 1 — Cover
        fig = plt.figure(figsize=(11.69, 8.27))
        gs = gridspec.GridSpec(1, 1, figure=fig)
        ax = fig.add_subplot(gs[0])
        hide_axis(ax)
        ax.add_patch(
            FancyBboxPatch(
                (0.03, 0.08),
                0.94,
                0.84,
                boxstyle="round,pad=0.02,rounding_size=18",
                linewidth=0,
                facecolor=COLORS["navy"],
                transform=ax.transAxes,
            )
        )
        ax.text(0.07, 0.78, "Menu Demand Report", fontsize=28, color="white", fontweight="bold", transform=ax.transAxes)
        ax.text(0.07, 0.68, "Отчёт по спросу, меню и сценариям изменений", fontsize=14, color="#CBD5E1", transform=ax.transAxes)
        ax.text(
            0.07,
            0.48,
            f"Базовая выручка: {fmt_money(b_rev)} ₽\n"
            f"Средний чек: {b_check:.1f} ₽\n"
            f"Вероятность роста при добавлении новой позиции: {p_add:.1f}%",
            fontsize=16,
            color="white",
            linespacing=1.6,
            transform=ax.transAxes,
        )
        ax.text(
            0.07,
            0.20,
            "Документ для принятия решений по меню и ценам.\n"
            "Фокус: выручка, риск, каннибализация, конкретные действия.",
            fontsize=11,
            color="#CBD5E1",
            transform=ax.transAxes,
        )
        add_footer(fig, 1)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # PAGE 2 — KPI cards
        fig = plt.figure(figsize=(11.69, 8.27))
        gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.25)
        fig.suptitle("1. Executive Summary", fontsize=18, fontweight="bold", color=COLORS["navy"], y=0.97)

        draw_kpi_card(
            fig.add_subplot(gs[0, 0]),
            "Прогноз выручки",
            f"{fmt_money(rev_low)} – {fmt_money(rev_high)} ₽",
            "Диапазон с учётом неопределённости",
            "blue",
        )
        draw_kpi_card(
            fig.add_subplot(gs[0, 1]),
            "Прогноз прибыли",
            f"{fmt_money(profit_low)} – {fmt_money(profit_high)} ₽",
            f"Оценка при марже {avg_margin_pct:.1f}%",
            "green",
        )
        draw_kpi_card(
            fig.add_subplot(gs[1, 0]),
            "Средний чек",
            f"{b_check:.1f} ₽",
            f"Среднее товаров в заказе: {b_items:.3f}",
            "amber",
        )
        draw_kpi_card(
            fig.add_subplot(gs[1, 1]),
            kpi_compare_title,
            f"{fmt_signed_rub(best_d)} ₽",
            f"{best_label}. {kpi_compare_hint}. P(роста) {best_p:.1f}%.",
            "green" if best_d > 0 else "amber" if best_d == 0 else "red",
        )

        add_footer(fig, 2)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # PAGE 3 — Verdict
        fig = plt.figure(figsize=(11.69, 8.27))
        gs = gridspec.GridSpec(1, 1, figure=fig)
        fig.suptitle("2. Вердикт", fontsize=18, fontweight="bold", color=COLORS["navy"], y=0.97)

        if d_add > 0:
            add_line = (
                f"Сценарий добавления «{add_name}» даёт {fmt_signed_rub(d_add)} ₽ к суммарной выручке в модели."
            )
        elif d_add < 0:
            add_line = (
                f"Сценарий добавления «{add_name}» в модели даёт {fmt_signed_rub(d_add)} ₽ "
                f"(каннибализация mains / позиция редко выигрывает выбор) — это не «нулевой рост», а просадка."
            )
        else:
            add_line = f"Сценарий добавления «{add_name}» почти не меняет суммарную выручку."

        summary_lines = [
            "Меню уже генерирует устойчивую выручку, но часть позиций создаёт внутреннюю конкуренцию и снижает эффект изменений.",
            "Сравнивайте сценарии по знаку Δ: отрицательная дельта означает ожидаемое снижение выручки в рамках текущей модели.",
            add_line,
            f"Удаление {remove_name}: {fmt_signed_rub(d_remove)} ₽ к выручке.",
            f"{price_scenario_human.capitalize()}: эффект по выручке {fmt_signed_rub(d_price)} ₽.",
        ]
        draw_text_panel(fig.add_subplot(gs[0, 0]), "Ключевой вывод", summary_lines, tone="blue", max_chars=95, base_fontsize=12.0)

        add_footer(fig, 3)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # PAGE 4 — Action plan
        fig = plt.figure(figsize=(11.69, 8.27))
        gs = gridspec.GridSpec(1, 2, figure=fig, wspace=0.25)
        fig.suptitle("3. Что делать прямо сейчас", fontsize=18, fontweight="bold", color=COLORS["navy"], y=0.97)

        if d_add > 0:
            step1 = f"1. Добавить {add_name} → ожидаемо {fmt_signed_rub(d_add)} ₽ к выручке"
        elif d_add < 0:
            step1 = (
                f"1. Не внедрять «как есть» {add_name}: в модели {fmt_signed_rub(d_add)} ₽ — "
                f"сменить цену, состав или кластер позиции и пересчитать"
            )
        else:
            step1 = f"1. Оценить {add_name} отдельно — Δ выручки ≈ 0 в текущем сценарии"

        action_lines = [
            step1,
            f"2. {price_scenario_human.capitalize()}: эффект {fmt_signed_rub(d_price)} ₽",
            f"3. Не удалять {remove_name}: эффект {fmt_signed_rub(d_remove)} ₽",
            "4. Усилить продвижение топ-3 блюд в витрине и на первом экране меню",
            "5. Провести A/B тест 1–2 недели и затем пересчитать веса модели по факту",
        ]
        draw_text_panel(fig.add_subplot(gs[0, 0]), "Action Plan", action_lines, tone="green", max_chars=48, base_fontsize=11.0)

        details_lines = [
            f"Добавляем: {add_name}",
            medium_item_desc(add_item),
            "",
            f"Оставляем: {remove_name}",
            medium_item_desc(remove_item),
            "",
            f"Без изменения цены: {price_name}",
            medium_item_desc(price_item),
        ]
        draw_text_panel(fig.add_subplot(gs[0, 1]), "Ключевые позиции", details_lines, tone="panel", max_chars=48, base_fontsize=11.0)

        add_footer(fig, 4)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # PAGE 5 — Unit economics
        fig = plt.figure(figsize=(11.69, 8.27))
        gs = gridspec.GridSpec(1, 1, figure=fig)
        fig.suptitle("4. Unit-экономика", fontsize=18, fontweight="bold", color=COLORS["navy"], y=0.97)

        unit_rows = [
            ["Выручка", f"{fmt_money(b_rev)} ₽", "Базовый сценарий"],
            ["Средний чек", f"{b_check:.2f} ₽", "По всем заказам"],
            ["Товаров в заказе", f"{b_items:.3f}", "Средняя корзина"],
            ["Средняя маржа", f"{avg_margin_pct:.1f}%", "Оценка при food cost 45%"],
            ["Точка безубыточности", f"{breakeven_orders_day:.1f} / день", "Оценочная"],
            ["Диапазон выручки", f"{fmt_money(rev_low)} – {fmt_money(rev_high)} ₽", "По uncertainty block"],
            ["Диапазон прибыли", f"{fmt_money(profit_low)} – {fmt_money(profit_high)} ₽", "Оценочный"],
        ]
        draw_table(fig.add_subplot(gs[0, 0]), "Основа юнит-экономики", ["Метрика", "Значение", "Комментарий"], unit_rows, font_size=9.3)

        add_footer(fig, 5)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # PAGE 6 — Money leaks
        fig = plt.figure(figsize=(11.69, 8.27))
        gs = gridspec.GridSpec(1, 1, figure=fig)
        fig.suptitle("5. Где теряются деньги", fontsize=18, fontweight="bold", color=COLORS["navy"], y=0.97)

        weak_lines = [
            f"Цена на {price_name} выглядит чувствительной для спроса.",
            f"Effective elasticity: {scenarios['price_up']['elasticity'].get('elasticity')}",
            f"Удаление {remove_name}: {fmt_signed_rub(d_remove)} ₽ к выручке.",
            "",
            "Каннибализация при add_item:",
        ]
        add_losers = scenarios["add_item"].get("cannibalization", {}).get("losers", [])[:6]
        for x in add_losers:
            weak_lines.append(f"— {ru_name(x['name'])}: {x['delta_orders']:+d} заказов")
        draw_text_panel(fig.add_subplot(gs[0, 0]), "Основные потери", weak_lines, tone="amber", max_chars=92, base_fontsize=11.5)

        add_footer(fig, 6)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # PAGE 7 — scenarios delta
        fig = plt.figure(figsize=(11.69, 8.27))
        gs = gridspec.GridSpec(1, 2, figure=fig, wspace=0.28)
        fig.suptitle("6. Сценарии: финансовый эффект", fontsize=18, fontweight="bold", color=COLORS["navy"], y=0.97)

        labels = [f"Цена {price_shift_lbl}", "Удаление", "Добавление"]
        deltas = [d_price, d_remove, d_add]
        probs = [p_price, p_remove, p_add]

        ax1 = fig.add_subplot(gs[0, 0])
        ax1.bar(labels, deltas, color=[COLORS["green"] if x >= 0 else COLORS["red"] for x in deltas])
        ax1.axhline(0, color=COLORS["navy"], linewidth=1)
        ax1.set_title("Δ выручки, ₽", fontweight="bold")
        clean_axis(ax1)

        ax2 = fig.add_subplot(gs[0, 1])
        ax2.bar(labels, probs, color=COLORS["blue"])
        ax2.set_ylim(0, 100)
        ax2.set_title("Вероятность роста выручки, %", fontweight="bold")
        clean_axis(ax2)

        add_footer(fig, 7)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # PAGE 8 — scenario summary table
        fig = plt.figure(figsize=(11.69, 8.27))
        gs = gridspec.GridSpec(1, 1, figure=fig)
        fig.suptitle("7. Сводка по сценариям", fontsize=18, fontweight="bold", color=COLORS["navy"], y=0.97)

        def scenario_verdict(d: float, p: float) -> str:
            if d > 0 and p >= 80:
                return "Позитивный"
            if d > 0:
                return "Плюс по Δ, низкая уверенность"
            if d < 0:
                return "Негативный"
            return "Нейтральный"

        scenario_rows = [
            [f"Цена {price_shift_lbl}", f"{fmt_signed_rub(d_price)} ₽", f"{p_price:.1f}%", scenario_verdict(d_price, p_price)],
            ["Удаление позиции", f"{fmt_signed_rub(d_remove)} ₽", f"{p_remove:.1f}%", scenario_verdict(d_remove, p_remove)],
            ["Добавление позиции", f"{fmt_signed_rub(d_add)} ₽", f"{p_add:.1f}%", scenario_verdict(d_add, p_add)],
        ]
        draw_table(
            fig.add_subplot(gs[0, 0]),
            "Сценарии в одном месте",
            ["Сценарий", "Δ выручки", "P(роста)", "Вывод"],
            scenario_rows,
            font_size=10.0,
        )

        add_footer(fig, 8)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # PAGE 9 — menu analysis top/bottom
        fig = plt.figure(figsize=(11.69, 8.27))
        gs = gridspec.GridSpec(1, 2, figure=fig, wspace=0.32)
        fig.suptitle("8. Анализ меню: сильные и слабые позиции", fontsize=18, fontweight="bold", color=COLORS["navy"], y=0.97)

        t_names = [ru_name(menu_item_map.get(i, {}).get("name", f"item_{i}")) for i, _ in top_items]
        t_vals = [v for _, v in top_items]
        b_names = [ru_name(menu_item_map.get(i, {}).get("name", f"item_{i}")) for i, _ in bottom_items]
        b_vals = [v for _, v in bottom_items]

        ax1 = fig.add_subplot(gs[0, 0])
        ax1.barh(t_names[::-1], t_vals[::-1], color=COLORS["green"])
        ax1.set_title("Топ-5 по спросу", fontweight="bold")
        ax1.set_xlabel("Заказы")
        clean_axis(ax1)

        ax2 = fig.add_subplot(gs[0, 1])
        ax2.barh(b_names[::-1], b_vals[::-1], color=COLORS["red"])
        ax2.set_title("Анти-топ-5 по спросу", fontweight="bold")
        ax2.set_xlabel("Заказы")
        clean_axis(ax2)

        add_footer(fig, 9)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # PAGE 10 — decisions by menu
        fig = plt.figure(figsize=(11.69, 8.27))
        gs = gridspec.GridSpec(1, 2, figure=fig, wspace=0.25)
        fig.suptitle("9. Решения по меню", fontsize=18, fontweight="bold", color=COLORS["navy"], y=0.97)

        keep_lines = [f"— {ru_name(menu_item_map[i].get('name', f'item_{i}'))}" for i, _, _, _ in keep_items]
        remove_lines = [f"— {ru_name(menu_item_map[i].get('name', f'item_{i}'))}" for i, _, _, _ in remove_items]
        tune_lines = [f"— {ru_name(menu_item_map[i].get('name', f'item_{i}'))}" for i, _, _, _ in tune_items]

        left_lines = (
            ["Держим:"] + keep_lines +
            ["", "Убираем/пересматриваем:"] + remove_lines
        )
        right_lines = (
            ["Требуют отдельной настройки:"] + tune_lines +
            [
                "",
                f"Новая позиция: {add_name}",
                medium_item_desc(add_item),
                f"Δ выручки (add_item): {fmt_signed_rub(d_add)} ₽",
            ]
        )

        draw_text_panel(fig.add_subplot(gs[0, 0]), "Приоритеты меню", left_lines, tone="blue", max_chars=48, base_fontsize=11.2)
        draw_text_panel(fig.add_subplot(gs[0, 1]), "Новая позиция и настройка", right_lines, tone="green", max_chars=48, base_fontsize=11.2)

        add_footer(fig, 10)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # PAGE 11 — ICP
        fig = plt.figure(figsize=(11.69, 8.27))
        gs = gridspec.GridSpec(1, 1, figure=fig)
        fig.suptitle("10. Клиент (ICP)", fontsize=18, fontweight="bold", color=COLORS["navy"], y=0.97)

        icp_lines = [
            "Ключевые сегменты synthetic users:",
            "— price-sensitive: быстро реагируют на рост цены",
            "— healthy-lifestyle: тяготеют к салатам и полезным позициям",
            "— middle / high income: выше толерантность к среднему чеку",
            "",
            f"Средний чек: ~{b_check:.0f} ₽",
            "Частота заказов: примерно 2–5 в неделю",
            "На выбор влияют: цена, perceived healthiness, формат блюда, контекст заказа",
        ]
        draw_text_panel(fig.add_subplot(gs[0, 0]), "ICP и поведение клиента", icp_lines, tone="panel", max_chars=92, base_fontsize=11.7)

        add_footer(fig, 11)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # PAGE 12 — risks
        fig = plt.figure(figsize=(11.69, 8.27))
        gs = gridspec.GridSpec(1, 1, figure=fig)
        fig.suptitle("11. Риски и диапазоны", fontsize=18, fontweight="bold", color=COLORS["navy"], y=0.97)

        risk_rows = [
            ["Рост себестоимости", "0.60", "-15% прибыли"],
            ["Демпинг конкурента", "0.40", "-20% выручки"],
            ["Ошибочная цена SKU", "0.35", "-8% прибыли"],
            ["Неверное удаление сильной позиции", "0.30", "локальная просадка спроса"],
        ]
        draw_table(fig.add_subplot(gs[0, 0]), "Риски", ["Риск", "Вероятность", "Влияние"], risk_rows, font_size=10.0)

        add_footer(fig, 12)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # PAGE 13 — stress test
        curve = scenarios["price_up"].get("elasticity_curve", {})
        points = curve.get("points", [])

        fig = plt.figure(figsize=(11.69, 8.27))
        gs = gridspec.GridSpec(1, 2, figure=fig, wspace=0.28)
        fig.suptitle("12. Стресс-тест цены", fontsize=18, fontweight="bold", color=COLORS["navy"], y=0.97)

        ax1 = fig.add_subplot(gs[0, 0])
        if points:
            x = [float(p["price_rub"]) for p in points]
            y = [float(p["demand"]) for p in points]
            ax1.plot(x, y, marker="o", linewidth=2.5, color=COLORS["blue"])
            ax1.fill_between(x, y, color=COLORS["blue_soft"], alpha=0.8)
            ax1.set_title(f"Стресс-тест цены: {price_name}", fontweight="bold")
            ax1.set_xlabel("Цена, ₽")
            ax1.set_ylabel("Спрос")
            clean_axis(ax1)
        else:
            hide_axis(ax1)
            ax1.text(0.5, 0.5, "Нет данных для stress-test", ha="center", va="center")

        stress_lines = [
            f"Кривая цена–спрос по «{price_name}» (сдвиги от базовой цены в симуляции).",
            f"Локальная эластичность: {curve.get('elasticity_local', 'n/a')}",
            "Чувствительность спроса к цене видна по наклону; при промо смотрите правый участок кривой.",
        ]
        draw_text_panel(fig.add_subplot(gs[0, 1]), "Вывод по стресс-тесту", stress_lines, tone="amber", max_chars=45, base_fontsize=11.2)

        add_footer(fig, 13)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # PAGE 14 — final conclusion
        fig = plt.figure(figsize=(11.69, 8.27))
        gs = gridspec.GridSpec(1, 1, figure=fig)
        fig.suptitle("13. Финальный вывод", fontsize=18, fontweight="bold", color=COLORS["navy"], y=0.97)

        if d_add > 0:
            growth_line = f"Потенциал по сценарию add_item: {fmt_signed_rub(d_add)} ₽ к выручке (текущий набор сценариев)."
            change_hint = f"Что проверить: развитие линейки вокруг {add_name} при пилоте."
        elif d_add < 0:
            growth_line = f"Потенциала роста по add_item в этой постановке нет: модель даёт {fmt_signed_rub(d_add)} ₽ к выручке."
            change_hint = (
                f"Что проверить: другая новая позиция, цена или категория вместо шаблона «{add_name}»."
            )
        else:
            growth_line = "Сценарий add_item почти не двигает выручку — потенциал роста в этом тесте не виден."
            change_hint = f"Что проверить: параметры позиции {add_name} и пересчёт симуляции."

        final_lines = [
            f"Текущая модель: {'прибыльная' if best_d > 0 else 'рискованная' if best_d < 0 else 'нейтральная'} по лучшему из трёх сценариев",
            change_hint,
            f"Что не делать: не удалять {remove_name} без замены; по цене «{price_name}»: сдвиг {price_shift_lbl} даёт {fmt_signed_rub(d_price)} ₽.",
            growth_line,
            "Следующий шаг: пилот 1–2 недели и сверка с фактом; при отрицательном add_item — менять гипотезу позиции, а не масштабировать её.",
        ]
        draw_text_panel(fig.add_subplot(gs[0, 0]), "Итог для бизнеса", final_lines, tone="green", max_chars=95, base_fontsize=12.0)

        add_footer(fig, 14)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Генерация нормального клиентского PDF-отчёта")
    parser.add_argument("--input", default="demand_report.json")
    parser.add_argument("--food", default="food.json")
    parser.add_argument("--output", default="client_report.pdf")
    args = parser.parse_args()

    os.environ.setdefault("MPLBACKEND", "Agg")
    os.environ.setdefault("MPLCONFIGDIR", str(Path.cwd() / ".mplconfig"))
    Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)

    report = load_json_file(
        Path(args.input),
        hint="Сначала соберите отчёт симуляции:\n"
        "  python simulate_demand.py --users users.json --food food.json",
    )
    food_payload = load_json_file(
        Path(args.food),
        hint="Сгенерируйте меню:\n  python create_food.py",
    )
    menu_item_map = idx_to_item_map(get_menu_items(food_payload))
    build_pdf(report, menu_item_map, Path(args.output))
    print(f"Done. PDF report: {args.output}")


if __name__ == "__main__":
    main()