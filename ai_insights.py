import pandas as pd


def _safe_number(row, key, default=0):
    value = row.get(key, default)

    if pd.isna(value):
        return default

    return value


def _format_inr(value):
    amount = int(round(abs(value), 0))
    return f"{chr(8377)}{amount:,}"


def _arrow(value):
    return chr(8593) if value >= 0 else chr(8595)


def _highlight(value):
    return f"<strong>{value}</strong>"


def _absolute_delta(current, change_pct):
    current = float(current or 0)
    change_pct = float(change_pct or 0)

    if change_pct == -100:
        previous = 0
    else:
        previous = current / (1 + (change_pct / 100))

    return current - previous


def _movement(value, up_word, down_word):
    return up_word if value >= 0 else down_word


def _issue_from_changes(completion_change, missed_change, drivers_change, earnings_change, orders_change_abs):
    # Priority 1: Completion drop + high missed → conversion loss
    if completion_change < -1 and missed_change > 5:
        return "Low completion is limiting order conversion"

    # Priority 2: Drivers up but earnings not growing proportionally
    if drivers_change > 5 and earnings_change < (drivers_change * 0.5):
        return "Driver supply increased but utilization is weak"

    # Priority 3: Both earnings and orders growing → demand growth
    if earnings_change > 3 and orders_change_abs > 0:
        return "Strong demand growth is driving revenue increase"

    # Priority 4: Isolated completion drop
    if completion_change < -2:
        return "Low completion is limiting order conversion"

    # Priority 5: High missed alone
    if missed_change > 10:
        return "High missed notifications are impacting conversions"

    # Priority 6: Low driver supply
    if drivers_change < -5:
        return "Low driver supply is limiting growth"

    return "Balanced performance but optimization opportunities exist"


def _action_from_issue(issue, earnings_delta, earnings, missed, avg_orders, drivers):
    recovery = max(abs(earnings_delta) * 0.65, earnings * 0.04, 10000)
    unlock = _highlight(_format_inr(recovery))

    if "missed" in issue:
        missed_10pct = max(int(missed * 0.10), 1)
        missed_earn = _highlight(_format_inr(earnings * 0.08))
        return (
            f"Reducing missed orders by 10% (~{missed_10pct} orders) can unlock "
            f"~{missed_earn} additional earnings. Focus on notification reliability "
            f"and driver response time improvements."
        )

    if "completion" in issue:
        return (
            f"Improve driver acceptance and reduce missed notifications to "
            f"increase completion by ~2–3%. This can recover ~{unlock} in earnings."
        )

    if "utilization" in issue:
        if drivers and avg_orders:
            target_orders = int(avg_orders * 1.15)
            return (
                f"Improve driver utilization by increasing orders per driver from "
            f"{int(avg_orders)} to {target_orders}. Better allocation can unlock ~{unlock}."
            )
        return f"Improve driver utilization by increasing orders per driver to unlock ~{unlock}."

    if "demand growth" in issue:
        return (
            f"Capitalize on demand momentum by ensuring supply availability "
            f"during peak hours. Protect high-demand routes to sustain current growth."
        )

    return f"Tune supply allocation and protect high-performing routes to unlock ~{unlock} in earnings."


def _performance_summary(city, earnings_change, completion_change, orders_change_abs, drivers_change):
    city_name = _city_title(city) if city != "all" else "The fleet overall"

    parts = []
    if earnings_change > 3 and orders_change_abs > 0:
        parts.append("strong demand growth")
    elif earnings_change < -3:
        parts.append("declining revenue")
    else:
        parts.append("stable revenue")

    if completion_change < -1:
        parts.append("requires efficiency improvements to maximize output")
    elif drivers_change > 5 and earnings_change < drivers_change * 0.5:
        parts.append("needs better driver utilization to match supply with revenue")
    else:
        parts.append("is showing consistent fulfillment")

    return f"Overall, {city_name} is showing {parts[0]} but {parts[1]}."


def _city_title(city):
    if str(city).lower() == "all":
        return "All Cities"

    return str(city).title()


def _trend_line(city, direction):
    city_name = _city_title(city)

    if direction == "downward":
        return f"{city_name} earnings are trending downward over the last 7 days."

    return f"{city_name} earnings are trending upward over the last 7 days."


def _build_insight(row, city_count=1):
    city = str(row.get("City", "all"))
    earnings = float(_safe_number(row, "Earnings"))
    earnings_change = float(_safe_number(row, "earnings_change"))
    completion_change = float(_safe_number(row, "completion_change"))
    orders_change_abs = int(_safe_number(row, "orders_change_abs"))
    missed_change = float(_safe_number(row, "missed_change"))
    drivers_change = float(_safe_number(row, "drivers_change"))
    missed = float(_safe_number(row, "missed_notifs_overall", 0))
    avg_orders = float(_safe_number(row, "avg_orders", 0))
    drivers = float(_safe_number(row, "Drivers Reported", 0))
    trend_direction = str(row.get("trend_direction", "upward"))

    earnings_delta = _absolute_delta(earnings, earnings_change)
    issue = _issue_from_changes(
        completion_change, missed_change, drivers_change,
        earnings_change, orders_change_abs
    )

    city_suffix = f" across {city_count} cities" if city == "all" else ""
    issue_display = f"{issue}{city_suffix}"

    earnings_direction = _movement(earnings_delta, "increased", "declined")
    completion_direction = _movement(completion_change, "increased", "decreased")
    orders_direction = _movement(orders_change_abs, "increased", "dropped")

    # Causal storytelling — each line shows what happened AND why it matters
    earnings_cause = "primarily driven by a rise in completed orders" if orders_change_abs > 0 else "despite order activity"
    completion_implication = "indicating minor inefficiencies in fulfillment" if completion_change < 0 else "reflecting improved driver efficiency"
    orders_impact = "directly contributing to higher earnings" if earnings_delta > 0 else "putting pressure on revenue"

    what_changed = {
        "earnings": (
            f"Earnings {_arrow(earnings_delta)} {earnings_direction} by "
            f"{_highlight(_format_inr(earnings_delta))}, {earnings_cause}."
        ),
        "completion": (
            f"Completion {_arrow(completion_change)} {completion_direction} "
            f"by {_highlight(f'{abs(completion_change):.1f}%')}, {completion_implication}."
        ),
        "orders": (
            f"Orders {_arrow(orders_change_abs)} {orders_direction} by "
            f"{_highlight(f'{abs(orders_change_abs):,}')}, {orders_impact}."
        ),
    }

    action_plan = _action_from_issue(issue, earnings_delta, earnings, missed, avg_orders, drivers)
    trend_line = _trend_line(city, trend_direction)
    perf_summary = _performance_summary(city, earnings_change, completion_change, orders_change_abs, drivers_change)

    return {
        "city": city,
        "city_label": _city_title(city),
        "key_issue": issue_display,
        "what_changed": what_changed,
        "action_plan": action_plan,
        "trend_line": trend_line,
        "performance_summary": perf_summary,
        "what": issue_display,
        "why": trend_line,
        "action": action_plan,
        "actionable_recommendation": action_plan,
    }


def _combined_row(city_df):
    city_count = len(city_df)
    total_earnings = city_df["Earnings"].sum()
    total_orders = city_df["Completed Orders"].sum()
    total_missed = city_df["missed_notifs_overall"].sum()
    total_drivers = city_df.get("Drivers Reported", pd.Series([0])).sum()

    def weighted_change(column):
        if column not in city_df.columns or not total_earnings:
            return 0

        return (
            city_df[column].fillna(0) * city_df["Earnings"].fillna(0)
        ).sum() / total_earnings

    first_day_total = city_df.get("first_day_earnings", pd.Series([0])).sum()
    last_day_total = city_df.get("last_day_earnings", pd.Series([0])).sum()
    trend_direction = "downward" if last_day_total < first_day_total else "upward"

    return {
        "City": "all",
        "Earnings": total_earnings,
        "Completed Orders": total_orders,
        "Completion %": city_df["Completion %"].mean(),
        "missed_notifs_overall": total_missed,
        "Login Hours": city_df["Login Hours"].mean(),
        "Distance Travelled": city_df["Distance Travelled"].mean(),
        "Drivers Reported": total_drivers,
        "earnings_change": weighted_change("earnings_change"),
        "completion_change": weighted_change("completion_change"),
        "orders_change": weighted_change("orders_change"),
        "orders_change_abs": city_df.get("orders_change_abs", pd.Series([0])).sum(),
        "missed_change": weighted_change("missed_change"),
        "drivers_change": weighted_change("drivers_change"),
        "first_day_earnings": first_day_total,
        "last_day_earnings": last_day_total,
        "trend_direction": trend_direction,
    }, city_count


# ============================================================
# MAIN INSIGHT GENERATOR
# ============================================================

def generate_city_insights(city_df: pd.DataFrame):

    insights = []

    if city_df.empty:
        return insights

    combined, city_count = _combined_row(city_df)
    insights.append(_build_insight(combined, city_count=city_count))

    for _, row in city_df.iterrows():
        insights.append(_build_insight(row, city_count=1))

    return insights


# ============================================================
# OPTIONAL: FORMAT FOR DISPLAY (HTML / TEXT)
# ============================================================

def format_insights(insights):

    formatted = []

    for ins in insights:
        changed = ins["what_changed"]
        text = (
            f"{ins['city_label']} -> "
            f"Issue: {ins['key_issue']} | "
            f"{changed['earnings']} {changed['completion']} {changed['orders']} | "
            f"Action: {ins['action_plan']}"
        )

        formatted.append(text)

    return formatted
