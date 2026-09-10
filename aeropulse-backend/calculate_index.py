import pandas as pd
import numpy as np


INPUT_FILE = "flights_cleaned.csv"


HORIZON_WEIGHTS = {
    1: 0.15,
    7: 0.25,
    15: 0.25,
    30: 0.20,
    45: 0.15
}


APPROVED_ROUTES = [
    ("DEL", "BOM"),
    ("BOM", "DEL"),
    ("DEL", "BLR"),
    ("BLR", "DEL"),
    ("BOM", "BLR"),
    ("BLR", "BOM"),
    ("DEL", "HYD"),
    ("HYD", "DEL")
]


PASSENGER_TRAFFIC = {
    ("DEL", "BOM"): 3426228,
    ("BOM", "DEL"): 3424641,
    ("DEL", "BLR"): 2350018,
    ("BLR", "DEL"): 2331024,
    ("BOM", "BLR"): 2083737,
    ("BLR", "BOM"): 2030837,
    ("DEL", "HYD"): 1638188,
    ("HYD", "DEL"): 1657730
}


def geometric_mean(values):
    values = pd.to_numeric(values, errors="coerce")
    values = values[values > 0]

    if len(values) == 0:
        return np.nan

    return np.exp(np.mean(np.log(values)))


def calculate_indices():

    # -----------------------------
    # Load data
    # -----------------------------

    df = pd.read_csv(INPUT_FILE)

    required_columns = [
        "origin",
        "destination",
        "search_date",
        "travel_date",
        "booking_horizon",
        "displayed_fare",
        "travel_class",
        "stops",
        "currency"
    ]

    missing = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    # -----------------------------
    # Clean / standardize
    # -----------------------------

    df["origin"] = (
        df["origin"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["destination"] = (
        df["destination"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["travel_class"] = (
        df["travel_class"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    df["currency"] = (
        df["currency"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["search_date"] = pd.to_datetime(
        df["search_date"],
        errors="coerce"
    )

    df["travel_date"] = pd.to_datetime(
        df["travel_date"],
        errors="coerce"
    )

    df["booking_horizon"] = pd.to_numeric(
        df["booking_horizon"],
        errors="coerce"
    )

    df["displayed_fare"] = pd.to_numeric(
        df["displayed_fare"],
        errors="coerce"
    )

    df["stops"] = pd.to_numeric(
        df["stops"],
        errors="coerce"
    )

    # -----------------------------
    # Apply Siva's filters
    # -----------------------------

    df = df[
        df["travel_class"] == "economy"
    ].copy()

    df = df[
        df["stops"] == 0
    ].copy()

    df = df[
        df["currency"] == "INR"
    ].copy()

    df = df[
        df["displayed_fare"].notna()
        & (df["displayed_fare"] > 0)
    ].copy()

    # -----------------------------
    # Approved routes
    # -----------------------------

    df["route"] = list(
        zip(df["origin"], df["destination"])
    )

    df = df[
        df["route"].isin(APPROVED_ROUTES)
    ].copy()

    # -----------------------------
    # Approved horizons
    # -----------------------------

    df = df[
        df["booking_horizon"].isin(
            HORIZON_WEIGHTS.keys()
        )
    ].copy()

    # -----------------------------
    # Date / horizon validation
    # -----------------------------

    expected_date = (
        df["search_date"]
        + pd.to_timedelta(
            df["booking_horizon"],
            unit="D"
        )
    )

    df = df[
        df["travel_date"] == expected_date
    ].copy()

    # -----------------------------
    # Remove duplicates
    # -----------------------------

    duplicate_columns = [
        "origin",
        "destination",
        "travel_date",
        "flight_number",
        "departure_time",
        "displayed_fare"
    ]

    duplicate_columns = [
        column
        for column in duplicate_columns
        if column in df.columns
    ]

    df = df.drop_duplicates(
        subset=duplicate_columns
    ).copy()

    # -----------------------------
    # Daily geometric mean
    # -----------------------------

    daily_gm = (
        df.groupby(
            [
                "search_date",
                "origin",
                "destination",
                "booking_horizon"
            ]
        )["displayed_fare"]
        .apply(geometric_mean)
        .reset_index(
            name="geometric_mean"
        )
    )

    # -----------------------------
    # Base period
    # -----------------------------

    dates = sorted(
        daily_gm["search_date"]
        .dropna()
        .unique()
    )

    if len(dates) >= 7:
        base_dates = dates[:7]
    else:
        base_dates = dates

    base_data = daily_gm[
        daily_gm["search_date"].isin(base_dates)
    ].copy()

    base_gm = (
        base_data.groupby(
            [
                "origin",
                "destination",
                "booking_horizon"
            ]
        )["geometric_mean"]
        .apply(geometric_mean)
        .reset_index(
            name="base_geometric_mean"
        )
    )

    # -----------------------------
    # Horizon index
    # -----------------------------

    index_data = daily_gm.merge(
        base_gm,
        on=[
            "origin",
            "destination",
            "booking_horizon"
        ],
        how="left"
    )

    index_data["horizon_index"] = (
        index_data["geometric_mean"]
        / index_data["base_geometric_mean"]
    ) * 100

    index_data["horizon_weight"] = (
        index_data["booking_horizon"]
        .map(HORIZON_WEIGHTS)
    )

    index_data["weighted_horizon_index"] = (
        index_data["horizon_index"]
        * index_data["horizon_weight"]
    )

    # -----------------------------
    # Route index
    # -----------------------------

    route_index = (
        index_data.groupby(
            [
                "search_date",
                "origin",
                "destination"
            ]
        )["weighted_horizon_index"]
        .sum()
        .reset_index(
            name="route_index"
        )
    )

    route_index["route"] = list(
        zip(
            route_index["origin"],
            route_index["destination"]
        )
    )

    # -----------------------------
    # Passenger weights
    # -----------------------------

    total_passengers = sum(
        PASSENGER_TRAFFIC.values()
    )

    passenger_weights = {
        route: passengers / total_passengers
        for route, passengers
        in PASSENGER_TRAFFIC.items()
    }

    route_index["passenger_weight"] = (
        route_index["route"]
        .map(passenger_weights)
    )

    # -----------------------------
    # National AeroPulse Index
    # -----------------------------

    route_index["weighted_route_index"] = (
        route_index["route_index"]
        * route_index["passenger_weight"]
    )

    national_index = (
        route_index.groupby(
            "search_date"
        )["weighted_route_index"]
        .sum()
        .reset_index(
            name="aeropulse_index"
        )
    )

    national_index = national_index.sort_values(
        "search_date"
    ).reset_index(drop=True)

    national_index["percentage_change"] = (
        national_index["aeropulse_index"]
        .pct_change()
        * 100
    )

    return {
        "data": df,
        "horizon": index_data,
        "route": route_index,
        "national": national_index
    }