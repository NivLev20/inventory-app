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

// Register only what is used, to keep the bundle small
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Filler, Legend, Tooltip);

// Canvas cannot use CSS variables directly, so read the current theme's values
function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function ChartPanel({ title, children }) {
  return (
    <section className="panel">
      <div className="panel-head"><h2>{title}</h2></div>
      <div className="chart-box">{children}</div>
    </section>
  );
}

const STOCK_TITLE = "Units on shelves, last 14 days";
const MOVES_TITLE = "Sold and delivered per day";

// "theme" is the React key, so charts are recreated with the new colors after a theme switch
export default function Charts({ analytics, theme }) {
  if (!analytics) {
    return (
      <>
        <ChartPanel title={STOCK_TITLE}><p className="empty">Loading…</p></ChartPanel>
        <ChartPanel title={MOVES_TITLE}><p className="empty">Loading…</p></ChartPanel>
      </>
    );
  }

  const brand = cssVar("--accent");
  const muted = cssVar("--muted");
  const line = cssVar("--line");
  const sold = cssVar("--sold");
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
      backgroundColor: (context) => {
        const { ctx, chartArea } = context.chart;
        if (!chartArea) return brand + "22";
        const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
        gradient.addColorStop(0, brand + "55");
        gradient.addColorStop(1, brand + "00");
        return gradient;
      },
      fill: true,
      tension: 0.3,
      pointRadius: 0,
      pointHoverRadius: 4,
      borderWidth: 2
    }]
  };

  const movementsData = {
    labels,
    datasets: [
      { label: "Sold", data: analytics.sales_trend.map((d) => d.units), backgroundColor: sold,
        borderRadius: 6, maxBarThickness: 18 },
      { label: "Delivered", data: analytics.restocks_trend.map((d) => d.units), backgroundColor: brand,
        borderRadius: 6, maxBarThickness: 18 }
    ]
  };
  const movementsOptions = {
    ...options,
    plugins: { legend: { display: true, labels: { color: muted, boxWidth: 12 } } }
  };

  return (
    <>
      <ChartPanel title={STOCK_TITLE}><Line key={theme} data={stockData} options={options} /></ChartPanel>
      <ChartPanel title={MOVES_TITLE}><Bar key={theme} data={movementsData} options={movementsOptions} /></ChartPanel>
    </>
  );
}
