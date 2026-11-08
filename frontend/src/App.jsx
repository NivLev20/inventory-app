import { useCallback, useEffect, useState, useRef } from "react";
import { api } from "./api.js";
import Header from "./components/Header.jsx";
import KpiCards from "./components/KpiCards.jsx";
import Charts from "./components/Charts.jsx";
import LowStockPanel from "./components/LowStockPanel.jsx";
import ProductsTable from "./components/ProductsTable.jsx";
import RestockHistory from "./components/RestockHistory.jsx";
import AddProductDialog from "./components/AddProductDialog.jsx";
import RestockDialog from "./components/RestockDialog.jsx";
import Toast from "./components/Toast.jsx";
import SimulatorCard from "./components/SimulatorCard.jsx";

const REFRESH_MS = 30000; // reload data every 30 seconds

export default function App() {
  const [products, setProducts] = useState([]);
  const [lowStock, setLowStock] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [restocks, setRestocks] = useState([]);
  const [apiUp, setApiUp] = useState(null); // null = still checking
  const [toast, setToast] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [restockTarget, setRestockTarget] = useState(null); // product being restocked
  const [simulation, setSimulation] = useState(null); // true / false, null until loaded
  const [theme, setTheme] = useState(() => document.documentElement.dataset.theme || "dark");

  const toastTimer = useRef(null);
  const notify = useCallback((message) => {
    setToast(message);
    clearTimeout(toastTimer.current); // a new message gets its full 2.5 s
    toastTimer.current = setTimeout(() => setToast(""), 2500);
  }, []);
  useEffect(() => () => clearTimeout(toastTimer.current), []);

  const loadAll = useCallback(async () => {
    try {
      const [a, p, l, r, sim] = await Promise.all([
        api.getAnalytics(),
        api.getProducts(),
        api.getLowStock(),
        api.getRestocks(),
        api.getSimulation()
      ]);
      setAnalytics(a);
      setProducts(p);
      setLowStock(l);
      setRestocks(r);
      setSimulation(sim.enabled);
      setApiUp(true);
    } catch (err) {
      setApiUp(false);
      notify("Could not load data: " + err.message);
    }
  }, [notify]);

  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("theme", next);
    } catch {
      // storage blocked (private mode): the switch still applies to this visit
    }
    setTheme(next);
  }

  useEffect(() => {
    loadAll();
    const timer = setInterval(loadAll, REFRESH_MS);
    return () => clearInterval(timer); // cleanup when the component is removed
  }, [loadAll]);


  async function handleRestock(product, quantity, note) {
    const updated = await api.restock(product.id, quantity, note);
    notify(`${updated.name}: stock is now ${updated.stock}`);
    await loadAll();
  }

  async function handleQuickOrder(product) {
    try {
      await handleRestock(product, product.suggested_reorder, "suggested reorder");
    } catch (err) {
      notify(err.message);
    }
  }

  async function handleAdd(product) {
    await api.addProduct(product);
    notify("Product added");
    await loadAll();
  }

  async function handleToggleSimulation(enabled) {
    try {
      const state = await api.setSimulation(enabled);
      setSimulation(state.enabled);
      notify(state.enabled ? "Simulator resumed" : "Simulator paused");
    } catch (err) {
      notify(err.message);
    }
  }

  async function handleRush() {
    try {
      const result = await api.rushHour();
      notify(`Rush hour: ${result.sales} sales, ${result.units} units sold`);
      await loadAll();
    } catch (err) {
      notify(err.message);
    }
  }

  async function handleDelete(product) {
    if (!window.confirm(`Delete "${product.name}"?`)) return;
    try {
      await api.deleteProduct(product.id);
      notify("Product deleted");
      await loadAll();
    } catch (err) {
      notify(err.message);
    }
  }

  return (
    <>
      <Header apiUp={apiUp} theme={theme} onToggleTheme={toggleTheme} onAddClick={() => setShowAdd(true)} />
      <main>
        <KpiCards analytics={analytics} />
        <LowStockPanel items={lowStock} onOrder={handleQuickOrder} />
        <div className="grid">
          <div className="stack">
            <Charts analytics={analytics} theme={theme} />
          </div>
          <div className="stack">
            <SimulatorCard enabled={simulation} onToggle={handleToggleSimulation} onRush={handleRush} />
            <RestockHistory restocks={restocks} />
          </div>
        </div>
        <ProductsTable
          products={products}
          onRestock={setRestockTarget}
          onDelete={handleDelete}
        />
      </main>

      {showAdd && (
        <AddProductDialog onSave={handleAdd} onClose={() => setShowAdd(false)} />
      )}
      {restockTarget && (
        <RestockDialog
          product={restockTarget}
          onSave={(qty, note) => handleRestock(restockTarget, qty, note)}
          onClose={() => setRestockTarget(null)}
        />
      )}
      <Toast message={toast} />
    </>
  );
}
