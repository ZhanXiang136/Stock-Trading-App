import React, { useEffect, useState } from 'react';
import { Line } from 'react-chartjs-2';
import 'chart.js/auto';

function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchPerformance = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/performance");
        if (!res.ok) throw new Error("Failed to fetch performance data");
        const json = await res.json();
        setData(json);
      } catch (err) {
        setError(err.message);
        console.error("❌ API Error:", err);
      }
    };

    fetchPerformance();
  }, []);

  if (error) return <p>Error: {error}</p>;
  if (!data) return <p>Loading...</p>;

  const labels = Object.keys(data.sp500);
  const sp500Values = Object.values(data.sp500);
  const nasdaqValues = Object.values(data.nasdaq);
  const botEquityLine = Array(labels.length).fill(data.bot_equity);

  const chartData = {
    labels,
    datasets: [
      {
        label: "Bot Equity (Flat Line)",
        data: botEquityLine,
        borderColor: "blue",
        fill: false,
      },
      {
        label: "S&P 500 %",
        data: sp500Values,
        borderColor: "green",
        fill: false,
      },
      {
        label: "NASDAQ %",
        data: nasdaqValues,
        borderColor: "red",
        fill: false,
      },
    ],
  };

  return (
    <div style={{ width: "80%", margin: "auto" }}>
      <h2>Trading Bot vs. Market Indices</h2>
      <Line data={chartData} />
    </div>
  );
}

export default App;
