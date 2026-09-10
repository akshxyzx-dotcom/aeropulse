import pandas as pd
import numpy as np
from pathlib import Path

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

TOTAL_PASSENGERS = sum(PASSENGER_TRAFFIC.values())

PASSENGER_WEIGHTS = {
    route: passengers / TOTAL_PASSENGERS
    for route, passengers in PASSENGER_TRAFFIC.items()
}


def geometric_mean(values):
    values = pd.to_numeric(values, errors="coerce")
    values = values[values > 0]

    if len(values) == 0:
        return np.nan

    return np.exp(np.mean(np.log(values)))


def calculate_demo_indices():
    """
    Calculate the Demo AeroPulse Index.

    Snapshot 1 = fixed base = 100.
    Returns data required by the FastAPI backend.
    """

    input_file = Path(__file__).parent / "flights_cleaned_demo.csv"
    
    df = pd.read_csv(input_file)

    # --------------------------------------------------------
    # Standardize data
    # --------------------------------------------------------

    required_columns = [
        "snapshot_id",
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

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    df["snapshot_id"] = pd.to_numeric(
        df["snapshot_id"],
        errors="coerce"
    )

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

    # --------------------------------------------------------
    # Filters
    # --------------------------------------------------------

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
        &
        (df["displayed_fare"] > 0)
    ].copy()

    df["route"] = list(
        zip(
            df["origin"],
            df["destination"]
        )
    )

    df = df[
        df["route"].isin(APPROVED_ROUTES)
    ].copy()

    df = df[
        df["booking_horizon"].isin(
            HORIZON_WEIGHTS.keys()
        )
    ].copy()

    # --------------------------------------------------------
    # Verify travel date
    # --------------------------------------------------------

    expected_travel_date = (
        df["search_date"]
        +
        pd.to_timedelta(
            df["booking_horizon"],
            unit="D"
        )
    )

    valid_dates = (
        df["travel_date"]
        == expected_travel_date
    )

    df = df[
        valid_dates
    ].copy()

    # --------------------------------------------------------
    # Remove duplicates
    # --------------------------------------------------------

    duplicate_columns = [
        "snapshot_id",
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

    # --------------------------------------------------------
    # Snapshot validation
    # --------------------------------------------------------

    snapshots = sorted(
        df["snapshot_id"]
        .dropna()
        .unique()
    )

    if 1 not in snapshots:
        raise ValueError(
            "Snapshot 1 was not found. "
            "Snapshot 1 is required as the fixed base."
        )

    # --------------------------------------------------------
    # Geometric mean
    # --------------------------------------------------------

    snapshot_gm = (
        df.groupby(
            [
                "snapshot_id",
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

    snapshot_gm["route"] = list(
        zip(
            snapshot_gm["origin"],
            snapshot_gm["destination"]
        )
    )

    # --------------------------------------------------------
    # Base = Snapshot 1
    # --------------------------------------------------------

    base_data = snapshot_gm[
        snapshot_gm["snapshot_id"] == 1
    ].copy()

    base_gm = (
        base_data.groupby(
            [
                "origin",
                "destination",
                "booking_horizon"
            ]
        )["geometric_mean"]
        .first()
        .reset_index(
            name="base_geometric_mean"
        )
    )

    # --------------------------------------------------------
    # Horizon index
    # --------------------------------------------------------

    index_data = snapshot_gm.merge(
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
        /
        index_data["base_geometric_mean"]
    ) * 100

    index_data["horizon_weight"] = (
        index_data["booking_horizon"]
        .map(HORIZON_WEIGHTS)
    )

    index_data["weighted_horizon_index"] = (
        index_data["horizon_index"]
        *
        index_data["horizon_weight"]
    )

    # --------------------------------------------------------
    # Route index
    # --------------------------------------------------------

    route_index = (
        index_data.groupby(
            [
                "snapshot_id",
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

    route_index["passenger_weight"] = (
        route_index["route"]
        .map(PASSENGER_WEIGHTS)
    )

    # --------------------------------------------------------
    # National AeroPulse index
    # --------------------------------------------------------

    route_index["weighted_route_index"] = (
        route_index["route_index"]
        *
        route_index["passenger_weight"]
    )

    national_index = (
        route_index.groupby(
            "snapshot_id"
        )["weighted_route_index"]
        .sum()
        .reset_index(
            name="aeropulse_index"
        )
    )

    # --------------------------------------------------------
    # Timestamp
    # --------------------------------------------------------

    if "collected_at" in df.columns:

        snapshot_times = (
            df.groupby(
                "snapshot_id"
            )["collected_at"]
            .first()
            .reset_index(
                name="collected_at"
            )
        )

        national_index = national_index.merge(
            snapshot_times,
            on="snapshot_id",
            how="left"
        )

    # --------------------------------------------------------
    # Percentage changes
    # --------------------------------------------------------

    national_index = (
        national_index
        .sort_values("snapshot_id")
        .reset_index(drop=True)
    )

    national_index["percentage_change"] = (
        national_index["aeropulse_index"]
        .pct_change()
        * 100
    )

    base_value = national_index.loc[
        national_index["snapshot_id"] == 1,
        "aeropulse_index"
    ].iloc[0]

    national_index["change_from_base"] = (
        (
            national_index["aeropulse_index"]
            - base_value
        )
        / base_value
    ) * 100

    # --------------------------------------------------------
    # RETURN RESULTS TO FASTAPI
    # --------------------------------------------------------

    return {
        "data": df,
        "horizon": index_data,
        "route": route_index,
        "national": national_index
    }