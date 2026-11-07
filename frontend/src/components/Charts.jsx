// Two charts: total stock over 14 days (line) and units sold vs restocked per day (bars).
// Chart.js draws the charts; react-chartjs-2 wraps it as React components.
import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip
} from "chart.js";
import { Bar, Line } from "react-chartjs-2";

// Chart.js only includes the parts you register (keeps the bundle small)
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Filler, Legend, Tooltip);

// Read colors from the CSS variables so charts match light and dark mode
function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

export default function Charts({ analytics }) {
  if (!analytics) {
    return (
      <section className="grid-2">
        <div className="card"><h2>Total stock – last 14 days</h2><p className="empty">Loading…</p></div>
        <div className="card"><h2>Units sold vs restocked per day</h2><p className="empty">Loading…</p></div>
      </section>
    );
  }

  const brand = cssVar("--brand");
  const muted = cssVar("--muted");
  const line = cssVar("--line");
  const sold = cssVar("--low");
  const labels = analytics.stock_trend.map((d) => d.date.slice(5)); // "11-07"

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: muted }, grid: { display: false } },
      y: { ticks: { color: muted }, grid: { color: line }, beginAtZero: true }
    }
  };

  const stockData = {
    labels,
    datasets: [{
      data: analytics.stock_trend.map((d) => d.total_units),
      borderColor: brand,
      backgroundColor: brand + "22",
      fill: true,
      tension: 0.3,
      pointRadius: 2
    }]
  };

  const movementsData = {
    labels,
    datasets: [
      { label: "Sold", data: analytics.sales_trend.map((d) => d.units), backgroundColor: sold, borderRadius: 4 },
      { label: "Restocked", data: analytics.restocks_trend.map((d) => d.units), backgroundColor: brand, borderRadius: 4 }
    ]
  };
  // Same look as the other chart, but with a legend (two series)
  const movementsOptions = {
    ...options,
    plugins: { legend: { display: true, labels: { color: muted, boxWidth: 12 } } }
  };

  return (
    <section className="grid-2">
      <div className="card">
        <h2>Total stock – last 14 days</h2>
        <div className="chart-box"><Line data={stockData} options={options} /></div>
      </div>
      <div className="card">
        <h2>Units sold vs restocked per day</h2>
        <div className="chart-box"><Bar data={movementsData} options={movementsOptions} /></div>
      </div>
    </section>
  );
}
