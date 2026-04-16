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


def _issue_from_changes(completion_change, missed_change, drivers_change):
    if completion_change < -2:
        return "Low completion is driving earnings drop"

    if missed_change > 10:
        return "High missed notifications are impacting conversions"

    if drivers_change < 0:
        return "Low driver supply is limiting growth"

    return "Balanced performance but optimization needed"


def _action_from_issue(issue, earnings_delta, earnings):
    recovery = max(abs(earnings_delta) * 0.65, earnings * 0.04, 10000)

    if "missed notifications" in issue:
        action = "Reduce missed notifications and improve alerting"
    elif "completion" in issue:
        action = "Improve driver acceptance and reduce cancellations"
    elif "driver supply" in issue:
        action = "Increase driver login hours and active supply"
    else:
        action = "Tune supply allocation and protect high-performing routes"

    return f"{action} to recover ~{_highlight(_format_inr(recovery))} in earnings."


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
    trend_direction = str(row.get("trend_direction", "upward"))

    earnings_delta = _absolute_delta(earnings, earnings_change)
    issue = _issue_from_changes(completion_change, missed_change, drivers_change)

    if city == "all":
        issue = f"{issue} across {city_count} cities"

    earnings_direction = _movement(earnings_delta, "increased", "declined")
    completion_direction = _movement(completion_change, "increased", "decreased")
    orders_direction = _movement(orders_change_abs, "increased", "dropped")

    what_changed = {
        "earnings": (
            f"Earnings {_arrow(earnings_delta)} have {earnings_direction} by "
            f"{_highlight(_format_inr(earnings_delta))}, indicating a shift in overall revenue momentum."
        ),
        "completion": (
            f"Completion rate {_arrow(completion_change)} {completion_direction} by "
            f"{_highlight(f'{abs(completion_change):.1f}%')}, changing efficiency in order fulfillment."
        ),
        "orders": (
            f"Total orders {_arrow(orders_change_abs)} {orders_direction} by "
            f"{_highlight(f'{abs(orders_change_abs):,} orders')}, directly impacting earnings."
        ),
    }
    action_plan = _action_from_issue(issue, earnings_delta, earnings)
    trend_line = _trend_line(city, trend_direction)

    return {
        "city": city,
        "city_label": _city_title(city),
        "key_issue": issue,
        "what_changed": what_changed,
        "action_plan": action_plan,
        "trend_line": trend_line,
        "what": issue,
        "why": trend_line,
        "action": action_plan,
        "performance_summary": issue,
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
