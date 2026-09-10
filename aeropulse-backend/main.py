from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from calculate_index import calculate_indices
from DEMO.calculate_index_demo_api import calculate_demo_indices
import numpy as np

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
        "http://localhost:5174",
        "http://127.0.0.1:5174"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_calculation(mode):
    if mode == "demo":
        return calculate_demo_indices()

    return calculate_indices()

@app.get("/")
def home():
    return {
        "message": "AeroPulse Backend is running!"
    }


@app.get("/api/summary")
def get_summary(mode: str = "real"):

    results = get_calculation(mode)

    data = results["data"]

    average_fare = float(
        data["displayed_fare"].mean()
    )

    national = results["national"]

    latest = national.iloc[-1]

    current_index = float(
        latest["aeropulse_index"]
    )

    change_percent = latest["percentage_change"]

    if change_percent != change_percent:
        change_percent = 0.0
    else:
        change_percent = float(change_percent)

    return {
        "current_index": round(current_index, 2),
        "average_fare": round(average_fare,2),
        "change_percent": round(change_percent, 2)
    }

@app.get("/api/index-history")
def get_index_history(mode: str = "real"):

    results = get_calculation(mode)

    national = results["national"]

    history = []

    for _, row in national.iterrows():

        history.append({
            "date": str(int(row["snapshot_id"])),
            "index": round(
                float(row["aeropulse_index"]),
                2
            )
        })

    return history

@app.get("/api/route-comparison")
def get_route_comparison(mode: str = "real"):

    results = get_calculation(mode)

    route_data = results["route"]

    comparison = []

    for _, row in route_data.iterrows():

        comparison.append({
            "route": f"{row['origin']}-{row['destination']}",
            "origin": row["origin"],
            "destination": row["destination"],
            "index": round(
                float(row["route_index"]),
                2
            )
        })

    return comparison

@app.get("/api/booking-horizon")
def get_booking_horizon(mode: str = "real"):

    results = get_calculation(mode)

    horizon_data = results["horizon"]

    horizon_list = []

    for _, row in horizon_data.iterrows():

        horizon_list.append({
            "snapshot_id": int(row["snapshot_id"]),
            "route": f"{row['origin']}-{row['destination']}",
            "horizon": f"T+{int(row['booking_horizon'])}",
            "index": round(
                float(row["horizon_index"]),
                2
            )
        })

    return horizon_list

@app.get("/api/route-analysis")
def get_route_analysis(
    origin: str,
    destination: str,
    mode: str = "real"
):
    origin = origin.strip().upper()
    destination = destination.strip().upper()

    results = get_calculation(mode)

    route_data = results["route"]

    selected = route_data[
        (route_data["origin"] == origin)
        & (route_data["destination"] == destination)
    ]

    if selected.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Route {origin}-{destination} is not an approved route"
        )

    # Get the latest snapshot for this route
    latest = selected.iloc[-1]

    route_index = float(latest["route_index"])

    if route_index > 100:
        status = "ABOVE AVERAGE"
    elif route_index < 100:
        status = "BELOW AVERAGE"
    else:
        status = "AVERAGE"

    return {
        "origin": origin,
        "destination": destination,
        "index": round(route_index, 2),
        "status": status
    }

@app.get("/api/route-prediction")
def get_route_prediction(
    origin: str,
    destination: str,
    mode: str = "real"
):
    origin = origin.strip().upper()
    destination = destination.strip().upper()

    results = get_calculation(mode)

    route_data = results["route"]

    selected = route_data[
        (route_data["origin"] == origin)
        & (route_data["destination"] == destination)
    ].copy()

    if selected.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Route {origin}-{destination} is not an approved route"
        )

    # Sort by snapshot
    selected = selected.sort_values("snapshot_id")

    # Need at least 2 observations for a trend
    if len(selected) < 2:
        raise HTTPException(
            status_code=400,
            detail="Not enough historical data for prediction"
        )

    x = selected["snapshot_id"].to_numpy(dtype=float)
    y = selected["route_index"].to_numpy(dtype=float)

    # Linear trend
    slope, intercept = np.polyfit(x, y, 1)

    next_snapshot = x[-1] + 1
    predicted_index = slope * next_snapshot + intercept

    return {
        "origin": origin,
        "destination": destination,
        "current_index": round(float(y[-1]), 2),
        "predicted_index": round(float(predicted_index), 2),
        "next_snapshot": int(next_snapshot),
        "method": "Linear Trend"
    }