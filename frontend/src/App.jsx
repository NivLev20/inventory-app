// App = the main component. It loads all data from the API, keeps it in "state",
// and passes pieces of it down to the smaller components as "props".
import { useCallback, useEffect, useState } from "react";
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

const REFRESH_MS = 30000; // reload data every 30 seconds

export default function App() {
  // --- state: data that, when changed, makes React redraw the screen
  const [products, setProducts] = useState([]);
  const [lowStock, setLowStock] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [restocks, setRestocks] = useState([]);
  const [apiUp, setApiUp] = useState(null); // null = still checking
  const [toast, setToast] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [restockTarget, setRestockTarget] = useState(null); // product being restocked

  const notify = useCallback((message) => {
    setToast(message);
    setTimeout(() => setToast(""), 2500);
  }, []);

  // Load everything from the backend in parallel
  const loadAll = useCallback(async () => {
    try {
      const [a, p, l, r] = await Promise.all([
        api.getAnalytics(),
        api.getProducts(),
        api.getLowStock(),
        api.getRestocks()
      ]);
      setAnalytics(a);
      setProducts(p);
      setLowStock(l);
      setRestocks(r);
      setApiUp(true);
    } catch (err) {
      setApiUp(false);
      notify("Could not load data: " + err.message);
    }
  }, [notify]);

  // Runs once when the page opens: first load + a timer for auto refresh
  useEffect(() => {
    loadAll();
    const timer = setInterval(loadAll, REFRESH_MS);
    return () => clearInterval(timer); // cleanup when the component is removed
  }, [loadAll]);

  // --- actions (passed down to child components)

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
      <Header apiUp={apiUp} onAddClick={() => setShowAdd(true)} />
      <main>
        <KpiCards analytics={analytics} />
        <Charts analytics={analytics} />
        <LowStockPanel items={lowStock} onOrder={handleQuickOrder} />
        <ProductsTable
          products={products}
          onRestock={setRestockTarget}
          onDelete={handleDelete}
        />
        <RestockHistory restocks={restocks} />
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
