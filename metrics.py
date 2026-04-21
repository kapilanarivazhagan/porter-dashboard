import pandas as pd

BASE_KPI_KEYS = (
    "earnings",
    "avg_earnings",
    "completion",
    "orders",
    "avg_orders",
    "missed",
    "drivers"
)


# ===============================
# FILTER DATA
# ===============================

def filter_data(df, target_date, city=None):

    target_date = pd.to_datetime(target_date).normalize()
    order_dates = pd.to_datetime(df["Order Date"], errors="coerce").dt.normalize()

    df_day = df[order_dates == target_date].copy()

    if city and city.lower() != "all":
        df_day = df_day[df_day["City"].astype(str).str.lower() == city.lower()]

    return df_day


# ===============================
# KPI CALCULATION
# ===============================

def calculate_kpis(df):

    if df.empty:
        return {key: 0 for key in BASE_KPI_KEYS}

    # -----------------------------
    # BASIC KPIs
    # -----------------------------
    total_earnings = df["Earnings"].sum()
    avg_earnings = df["Earnings"].mean()

    total_orders = df["Completed Orders"].sum()
    avg_orders = df["Completed Orders"].mean()

    total_missed = df["missed_notifs_overall"].sum()

    # -----------------------------
    # COMPLETION
    # -----------------------------
    completion = df["Completion %"].mean()

    # -----------------------------
    # DRIVERS
    # -----------------------------
    if "Driver Name" in df.columns:
        drivers = df["Driver Name"].nunique()
    else:
        drivers = 0

    # -----------------------------
    # CLEAN OUTPUT
    # -----------------------------
    return {
        "earnings": int(round(total_earnings, 0)),
        "avg_earnings": int(round(avg_earnings, 0)),
        "completion": float(round(completion, 1)),
        "orders": int(total_orders),
        "avg_orders": int(round(avg_orders, 0)),
        "missed": int(total_missed),
        "drivers": int(drivers)
    }


# ===============================
# CHANGE CALCULATION
# ===============================

def calculate_changes(today_kpis, yday_kpis):

    changes = {}

    for key in BASE_KPI_KEYS:

        today = today_kpis.get(key, 0) or 0
        yday = yday_kpis.get(key, 0) or 0

        if yday == 0:
            changes[f"{key}_change"] = 0
        else:
            change = ((today - yday) / yday) * 100
            changes[f"{key}_change"] = round(change, 1)

    changes["orders_change_abs"] = (
        (today_kpis.get("orders", 0) or 0)
        - (yday_kpis.get("orders", 0) or 0)
    )

    return changes

# ===============================
# CITY-WISE AGGREGATION
# ===============================

def city_metrics(df):

    agg_dict = {
        "Earnings": "sum",
        "Completed Orders": "sum",
        "Login Hours": "mean",
        "Distance Travelled": "mean",
        "Completion %": "mean",
        "missed_notifs_overall": "sum"
    }

    if "Driver Name" in df.columns:
        agg_dict["Driver Name"] = pd.Series.nunique

    city_df = df.groupby("City").agg(agg_dict).reset_index()

    if "Driver Name" in city_df.columns:
        city_df.rename(columns={"Driver Name": "Drivers Reported"}, inplace=True)

    return city_df


def add_city_changes(city_data, df_today, df_yday):

    city_data = city_data.copy()

    for key in BASE_KPI_KEYS:
        city_data[f"{key}_change"] = 0.0
    city_data["orders_change_abs"] = 0

    if city_data.empty:
        return city_data

    for idx, row in city_data.iterrows():
        city = row["City"]

        today_kpis = calculate_kpis(df_today[df_today["City"] == city])
        yday_kpis = calculate_kpis(df_yday[df_yday["City"] == city])
        changes = calculate_changes(today_kpis, yday_kpis)

        for change_key, value in changes.items():
            city_data.at[idx, change_key] = value

    return city_data


# ===============================
# CHART DATA
# ===============================

def get_last_7_days_earnings(df, target_date):

    trend_df = df.copy()
    target_date = pd.to_datetime(target_date).normalize()
    trend_df["Order Date"] = pd.to_datetime(trend_df["Order Date"], errors="coerce").dt.normalize()
    trend_df = trend_df.dropna(subset=["Order Date"])

    # Remove Sundays (dayofweek 6)
    trend_df = trend_df[trend_df["Order Date"].dt.dayofweek != 6]

    if trend_df.empty:
        return pd.DataFrame(columns=["Order Date", "City", "Earnings"])

    last_7_days = trend_df[
        (trend_df["Order Date"] <= target_date)
        & (trend_df["Order Date"] >= target_date - pd.Timedelta(days=6))
    ]

    trend = (
        last_7_days
        .groupby(["Order Date", "City"], as_index=False)["Earnings"]
        .sum()
        .reset_index(drop=True)
        .sort_values("Order Date")
    )

    trend = trend[trend["Earnings"] > 0]

    total_trend = (
        trend
        .groupby("Order Date")["Earnings"]
        .sum()
        .reset_index()
    )
    total_trend["City"] = "All Cities"

    trend = pd.concat([trend, total_trend], ignore_index=True)

    return trend


def get_city_driver_earnings(df, target_date):

    df_copy = df.copy()
    target_date = pd.to_datetime(target_date).normalize()
    df_copy["Order Date"] = pd.to_datetime(df_copy["Order Date"], errors="coerce").dt.normalize()

    today_df = df_copy[df_copy["Order Date"] == target_date]

    # Try "Driver ID", fallback to "Driver Name" if missing
    driver_col = "Driver ID" if "Driver ID" in today_df.columns else "Driver Name"
    if driver_col not in today_df.columns:
        today_df[driver_col] = 0

    result = (
        today_df
        .groupby("City")
        .agg({
            "Earnings": "sum",
            driver_col: "nunique"
        })
        .reset_index()
    )

    result.rename(columns={driver_col: "Drivers Reported"}, inplace=True)

    return result


def add_trend_context(city_data, earnings_trend):

    city_data = city_data.copy()
    city_data["first_day_earnings"] = 0
    city_data["last_day_earnings"] = 0
    city_data["trend_direction"] = "flat"

    if isinstance(earnings_trend, pd.DataFrame):
        trend_df = earnings_trend.copy()
        if trend_df.empty:
            return city_data
        trend_df["city"] = trend_df["City"].astype(str)
        trend_df["date"] = pd.to_datetime(trend_df["Order Date"], errors="coerce")
        trend_df["earnings"] = trend_df["Earnings"]
    else:
        records = earnings_trend.get("records", []) if isinstance(earnings_trend, dict) else earnings_trend
        if not records:
            return city_data
        trend_df = pd.DataFrame(records)

    if city_data.empty:
        return city_data

    for idx, row in city_data.iterrows():
        city = row["City"]
        city_trend = trend_df[trend_df["city"] == city].sort_values("date")

        if city_trend.empty:
            continue

        first_day = int(city_trend.iloc[0]["earnings"])
        last_day = int(city_trend.iloc[-1]["earnings"])

        if last_day > first_day:
            direction = "upward"
        elif last_day < first_day:
            direction = "downward"
        else:
            direction = "flat"

        city_data.at[idx, "first_day_earnings"] = first_day
        city_data.at[idx, "last_day_earnings"] = last_day
        city_data.at[idx, "trend_direction"] = direction

    return city_data


def prepare_charts(df, target_date=None):

    chart_df = df.copy()
    chart_df["Order Date"] = pd.to_datetime(chart_df["Order Date"], errors="coerce")
    chart_df = chart_df.dropna(subset=["Order Date"])
    city_earnings = chart_df.groupby("City")["Earnings"].sum().reset_index()
    if target_date is None and not chart_df.empty:
        target_date = chart_df["Order Date"].max()

    city_earnings_trend = get_last_7_days_earnings(chart_df, target_date)
    driver_earnings_chart = get_city_driver_earnings(chart_df, target_date)

    return {
        "city_earnings": city_earnings,
        "city_earnings_trend": city_earnings_trend,
        "driver_earnings_chart": driver_earnings_chart
    }


# ===============================
# MAIN METRICS FUNCTION
# ===============================

def build_metrics(df, target_date, city=None):

    target_date = pd.to_datetime(target_date)
    yday = target_date - pd.Timedelta(days=1)

    if yday.weekday() == 6:
        yday = target_date - pd.Timedelta(days=2)
    # -----------------------------
    # TODAY DATA
    # -----------------------------
    df_today = filter_data(df, target_date, city)

    # -----------------------------
    # YESTERDAY DATA
    # -----------------------------
    df_yday = filter_data(df, yday, city)

    # -----------------------------
    # KPI CALCULATIONS
    # -----------------------------
    kpis_today = calculate_kpis(df_today)
    kpis_yday = calculate_kpis(df_yday)

    # -----------------------------
    # MERGE YDAY VALUES WITHOUT MUTATING DURING ITERATION
    # -----------------------------
    yday_values = {
        f"{key}_yday": kpis_yday.get(key, 0)
        for key in BASE_KPI_KEYS
    }

    # -----------------------------
    # ADD CHANGES
    # -----------------------------
    changes = calculate_changes(kpis_today, kpis_yday)
    kpis = {
        **kpis_today,
        **yday_values,
        **changes
    }

    # -----------------------------
    # OTHER DATA
    # -----------------------------
    charts = prepare_charts(df, target_date)
    city_data = add_city_changes(city_metrics(df_today), df_today, df_yday)
    city_data = add_trend_context(city_data, charts["city_earnings_trend"])

    return {
        "kpis": kpis,
        "city_data": city_data,
        "charts": charts
    }
