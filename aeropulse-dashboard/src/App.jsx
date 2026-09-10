import React from "react";
import "./App.css";

import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell
} from "recharts";

const API_BASE_URL = "http://127.0.0.1:8000";
const API_MODE = "demo";

function App() {

  // =========================
  // STATE
  // =========================

  const [summary, setSummary] = React.useState({
    current_index: 0,
    average_fare: 0,
    change_percent: 0
  });

  const [indexData, setIndexData] = React.useState([]);
  const [routeData, setRouteData] = React.useState([]);
  const [horizonData, setHorizonData] = React.useState([]);

  const [from, setFrom] = React.useState("DEL");
  const [to, setTo] = React.useState("BOM");

  const [routeAnalysis, setRouteAnalysis] = React.useState({
    index: 0,
    status: "LOADING..."
  });

  const [prediction, setPrediction] = React.useState({
    trend: "LOADING...",
    strength: "-",
    confidence: "-"
  });

  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState("");


  // =========================
  // LOAD DASHBOARD DATA
  // =========================

  React.useEffect(() => {

    async function loadDashboard() {

      try {

        setLoading(true);
        setError("");

        const [
          summaryResponse,
          historyResponse,
          routeResponse,
          horizonResponse
        ] = await Promise.all([

          fetch(
            `${API_BASE_URL}/api/summary?mode=${API_MODE}`
          ),

          fetch(
            `${API_BASE_URL}/api/index-history?mode=${API_MODE}`
          ),

          fetch(
            `${API_BASE_URL}/api/route-comparison?mode=${API_MODE}`
          ),

          fetch(
            `${API_BASE_URL}/api/booking-horizon?mode=${API_MODE}`
          )

        ]);


        if (
          !summaryResponse.ok ||
          !historyResponse.ok ||
          !routeResponse.ok ||
          !horizonResponse.ok
        ) {

          throw new Error(
            "Failed to load dashboard data"
          );

        }


        const summaryJson =
          await summaryResponse.json();

        const historyJson =
          await historyResponse.json();

        const routeJson =
          await routeResponse.json();

        const horizonJson =
          await horizonResponse.json();


        // =========================
        // SUMMARY
        // =========================

        setSummary(summaryJson);


        // =========================
        // INDEX HISTORY
        // =========================

        setIndexData(

          historyJson.map((item) => ({

            date: `Snapshot ${item.date}`,

            index: Number(item.index)

          }))

        );


        // =========================
        // ROUTE COMPARISON
        // Show only latest 8 routes
        // =========================

        const latestRoutes =
          routeJson.slice(-8);


        setRouteData(

          latestRoutes.map((item) => ({

            route:
              `${item.origin} → ${item.destination}`,

            index: Number(item.index)

          }))

        );


        // =========================
        // BOOKING HORIZON
        // Show only latest snapshot
        // =========================

        const latestSnapshot =

          horizonJson.length > 0
            ? Math.max(
                ...horizonJson.map(
                  (item) => Number(item.snapshot_id)
                )
              )
            : null;


        const latestHorizons =

          horizonJson.filter(

            (item) =>
              Number(item.snapshot_id) ===
              latestSnapshot

          );


        setHorizonData(

          latestHorizons.map((item) => ({

            horizon: item.horizon,

            index: Number(item.index),

            route: item.route,

            snapshot_id: item.snapshot_id

          }))

        );


      } catch (err) {

        console.error(
          "Dashboard error:",
          err
        );

        setError(
          "Unable to connect to the AeroPulse backend."
        );

      } finally {

        setLoading(false);

      }

    }


    loadDashboard();

  }, []);


  // =========================
  // LOAD ROUTE ANALYSIS
  // =========================

  React.useEffect(() => {

    async function loadRouteAnalysis() {

      try {

        setRouteAnalysis({

          index: 0,

          status: "LOADING..."

        });


        const response = await fetch(

          `${API_BASE_URL}/api/route-analysis?origin=${from}&destination=${to}&mode=${API_MODE}`

        );


        if (!response.ok) {

          throw new Error(
            "Route not available"
          );

        }


        const data =
          await response.json();


        setRouteAnalysis(data);


      } catch (err) {

        console.error(
          "Route analysis error:",
          err
        );


        setRouteAnalysis({

          index: 0,

          status: "DATA NOT AVAILABLE"

        });

      }

    }


    loadRouteAnalysis();

  }, [from, to]);


  // =========================
  // LOAD ROUTE PREDICTION
  // =========================

  React.useEffect(() => {

    async function loadPrediction() {

      try {

        setPrediction({

          trend: "LOADING...",

          strength: "-",

          confidence: "-"

        });


        const response = await fetch(

          `${API_BASE_URL}/api/route-prediction?origin=${from}&destination=${to}&mode=${API_MODE}`

        );


        if (!response.ok) {

          throw new Error(
            "Prediction not available"
          );

        }


        const data =
          await response.json();


        let trend = "STABLE";

        let strength = "Low";


        if (
          data.predicted_index >
          data.current_index
        ) {

          trend = "UPWARD TREND";

        }

        else if (
          data.predicted_index <
          data.current_index
        ) {

          trend = "DOWNWARD TREND";

        }


        const difference = Math.abs(

          data.predicted_index -
          data.current_index

        );


        if (difference >= 5) {

          strength = "Strong";

        }

        else if (difference >= 1) {

          strength = "Moderate";

        }


        setPrediction({

          trend,

          strength,

          confidence: "-"

        });


      } catch (err) {

        console.error(
          "Prediction error:",
          err
        );


        setPrediction({

          trend: "NO DATA",

          strength: "-",

          confidence: "-"

        });

      }

    }


    loadPrediction();

  }, [from, to]);


  // =========================
  // LOADING SCREEN
  // =========================

  if (loading) {

    return (

      <div className="dashboard">

        <div className="header">

          <h1>AEROPULSE</h1>

          <p>
            Airfare Price Intelligence
          </p>

        </div>


        <div
          style={{
            background: "#ffffff",
            padding: "40px",
            borderRadius: "12px",
            textAlign: "center"
          }}
        >

          Loading AeroPulse data...

        </div>

      </div>

    );

  }


  // =========================
  // DASHBOARD
  // =========================

  return (

    <div className="dashboard">


      {/* HEADER */}

      <header className="header">

        <div>

          <h1>AEROPULSE</h1>

          <p>
            Airfare Price Intelligence
          </p>

        </div>

      </header>


      {/* ERROR */}

      {error && (

        <div
          style={{
            background: "#fff4e5",
            color: "#b45309",
            padding: "10px 15px",
            borderRadius: "8px",
            marginBottom: "10px"
          }}
        >

          {error}

        </div>

      )}


      {/* KPI CARDS */}

      <section className="kpi-container">


        <div className="kpi-card">

          <span>
            Current Index
          </span>

          <strong>

            {Number(
              summary.current_index
            ).toFixed(2)}

          </strong>

        </div>


        <div className="kpi-card">

          <span>
            Average Fare
          </span>

          <strong>

            ₹
            {Number(
              summary.average_fare
            ).toLocaleString("en-IN")}

          </strong>

        </div>


        <div className="kpi-card change-card">

          <span>
            7-Day Change
          </span>

          <strong>

            {summary.change_percent >= 0
              ? "+"
              : ""}

            {Number(
              summary.change_percent
            ).toFixed(2)}%

            {summary.change_percent >= 0
              ? " ↑"
              : " ↓"}

          </strong>

        </div>


      </section>


      {/* MAIN CONTENT */}

      <section className="content">


        {/* =========================
            AIRFARE INDEX
        ========================= */}

        <div className="panel index-panel">

          <div className="panel-heading">

            <h2>
              Airfare Index Trend
            </h2>

            <p>
              Last 30 Days
            </p>

          </div>


          <div className="chart-container index-chart">

            <ResponsiveContainer
              width="100%"
              height="100%"
            >

              <AreaChart
                data={indexData}
                margin={{
                  top: 10,
                  right: 15,
                  left: 0,
                  bottom: 5
                }}
              >

                <defs>

                  <linearGradient
                    id="indexArea"
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >

                    <stop
                      offset="0%"
                      stopColor="#19b8c9"
                      stopOpacity={0.35}
                    />

                    <stop
                      offset="100%"
                      stopColor="#19b8c9"
                      stopOpacity={0.04}
                    />

                  </linearGradient>

                </defs>


                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#dce8ed"
                />


                <XAxis
                  dataKey="date"
                  tick={{
                    fill: "#52616b",
                    fontSize: 11
                  }}
                  axisLine={{
                    stroke: "#b9cbd3"
                  }}
                  tickLine={false}
                />


                <YAxis
                  tick={{
                    fill: "#52616b",
                    fontSize: 11
                  }}
                  axisLine={false}
                  tickLine={false}
                />


                <Tooltip

                  formatter={(value) => [

                    Number(value).toFixed(2),

                    "Index"

                  ]}

                  contentStyle={{
                    borderRadius: "8px",
                    border:
                      "1px solid #d5e3e8"
                  }}

                />


                <Area

                  type="monotone"

                  dataKey="index"

                  stroke="#08a8bb"

                  strokeWidth={3}

                  fill="url(#indexArea)"

                  dot={{
                    r: 4,
                    fill: "#ffffff",
                    stroke: "#087ea4",
                    strokeWidth: 2
                  }}

                  activeDot={{
                    r: 6
                  }}

                />

              </AreaChart>

            </ResponsiveContainer>

          </div>

        </div>


        {/* =========================
            ROUTE COMPARISON
        ========================= */}

        <div className="panel route-chart-panel">

          <div className="panel-heading">

            <h2>
              Route Comparison
            </h2>

            <p>
              Latest Snapshot
            </p>

          </div>


          <div className="chart-container small-chart">

            <ResponsiveContainer
              width="100%"
              height="100%"
            >

              <BarChart
                data={routeData}
                margin={{
                  top: 15,
                  right: 10,
                  left: -10,
                  bottom: 5
                }}
              >

                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#dce8ed"
                />


                <XAxis
                  dataKey="route"
                  tick={{
                    fill: "#52616b",
                    fontSize: 10
                  }}
                  axisLine={{
                    stroke: "#b9cbd3"
                  }}
                  tickLine={false}
                />


                <YAxis
                  tick={{
                    fill: "#52616b",
                    fontSize: 10
                  }}
                  axisLine={false}
                  tickLine={false}
                />


                <Tooltip

                  formatter={(value) => [

                    Number(value).toFixed(2),

                    "Route Index"

                  ]}

                  contentStyle={{
                    borderRadius: "8px",
                    border:
                      "1px solid #d5e3e8"
                  }}

                />


                <Bar
                  dataKey="index"
                  radius={[
                    6,
                    6,
                    0,
                    0
                  ]}
                >

                  {routeData.map(
                    (entry, index) => (

                      <Cell

                        key={`cell-${index}`}

                        fill={[

                          "#155b91",
                          "#18b5c4",
                          "#7fcf91",
                          "#277baa",
                          "#55a9b9"

                        ][index % 5]}

                      />

                    )
                  )}

                </Bar>

              </BarChart>

            </ResponsiveContainer>

          </div>

        </div>


        {/* =========================
            BOOKING HORIZON
        ========================= */}

        <div className="panel horizon-panel">

          <div className="panel-heading">

            <h2>
              Booking Horizon
            </h2>

            <p>
              Latest Snapshot
            </p>

          </div>


          <div className="chart-container small-chart">

            <ResponsiveContainer
              width="100%"
              height="100%"
            >

              <BarChart
                data={horizonData}
                margin={{
                  top: 15,
                  right: 10,
                  left: -10,
                  bottom: 5
                }}
              >

                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#dce8ed"
                />


                <XAxis
                  dataKey="horizon"
                  tick={{
                    fill: "#52616b",
                    fontSize: 10
                  }}
                  axisLine={{
                    stroke: "#b9cbd3"
                  }}
                  tickLine={false}
                />


                <YAxis
                  tick={{
                    fill: "#52616b",
                    fontSize: 10
                  }}
                  axisLine={false}
                  tickLine={false}
                />


                <Tooltip

                  formatter={(value) => [

                    Number(value).toFixed(2),

                    "Index"

                  ]}

                  contentStyle={{
                    borderRadius: "8px",
                    border:
                      "1px solid #d5e3e8"
                  }}

                />


                <Bar

                  dataKey="index"

                  fill="#155b91"

                  radius={[
                    5,
                    5,
                    0,
                    0
                  ]}

                />

              </BarChart>

            </ResponsiveContainer>

          </div>

        </div>


      </section>


      {/* =========================
          ROUTE ANALYSIS
      ========================= */}

      <section className="route-analysis">


        <div className="route-title">

          <h2>
            Route Analysis
          </h2>

        </div>


        {/* FROM / TO */}

        <div className="route-controls">


          <label>

            <span>
              From
            </span>

            <select
              value={from}
              onChange={(e) =>
                setFrom(e.target.value)
              }
            >

              <option value="DEL">
                Delhi (DEL)
              </option>

              <option value="BOM">
                Mumbai (BOM)
              </option>

              <option value="BLR">
                Bangalore (BLR)
              </option>

              <option value="HYD">
                Hyderabad (HYD)
              </option>

            </select>

          </label>


          <label>

            <span>
              To
            </span>

            <select
              value={to}
              onChange={(e) =>
                setTo(e.target.value)
              }
            >

              <option value="DEL">
                Delhi (DEL)
              </option>

              <option value="BOM">
                Mumbai (BOM)
              </option>

              <option value="BLR">
                Bangalore (BLR)
              </option>

              <option value="HYD">
                Hyderabad (HYD)
              </option>

            </select>

          </label>


        </div>


        {/* RESULTS */}

        <div className="route-result">


          <div className="result-box">

            <span>
              Average Fare
            </span>

            <strong>

              ₹
              {Number(
                summary.average_fare
              ).toLocaleString("en-IN")}

            </strong>

          </div>


          <div className="result-box">

            <span>
              Index
            </span>

            <strong>

              {Number(
                routeAnalysis.index
              ).toFixed(2)}

            </strong>

          </div>


          <div className="result-box status-box">

            <span>
              Status
            </span>

            <strong>

              {routeAnalysis.status}

            </strong>

          </div>


          <div className="result-box prediction-box">

            <span>
              Route Prediction
            </span>

            <strong>

              {prediction.trend}

            </strong>

            <small>

              {prediction.strength}

            </small>

            <small>

              Confidence:
              {" "}
              {prediction.confidence}

            </small>

          </div>


        </div>


      </section>


    </div>

  );

}


export default App;