"""
Store activity simulator. Runs as Kubernetes CronJobs to keep the demo system "alive".

    python simulator.py sales         # every minute: a few customer purchases,
                                      # plus supplier deliveries for sold-out items
    python simulator.py new-product   # every 2 minutes: launch the next product from a catalog

It only talks to the public REST API (like a real client would), never to the database.
API address: SIM_API_URL environment variable (default http://backend:5000).
"""
import json
import os
import random
import sys
import urllib.error
import urllib.request

STORES = ["Tel Aviv", "Haifa", "Jerusalem"]

# Products that "arrive" one by one. Limited on purpose, so the demo never grows forever.
CATALOG = [
    # name, sku, category, price, min_stock
    ("Wireless Earbuds", "NEW-001", "Electronics", 179.0, 10),
    ("Smart Watch Strap", "NEW-002", "Electronics", 59.9, 15),
    ("Power Bank 20000mAh", "NEW-003", "Electronics", 139.0, 8),
    ("Webcam 1080p", "NEW-004", "Electronics", 229.0, 6),
    ("Green Tea 100 bags", "NEW-005", "Grocery", 24.9, 30),
    ("Dark Chocolate 100g", "NEW-006", "Grocery", 11.9, 40),
    ("Hummus 400g", "NEW-007", "Grocery", 9.9, 50),
    ("Granola 500g", "NEW-008", "Grocery", 19.9, 25),
    ("Scented Candle", "NEW-009", "Home", 34.9, 12),
    ("Cutting Board", "NEW-010", "Home", 44.9, 10),
    ("Storage Box", "NEW-011", "Home", 29.9, 15),
    ("Desk Lamp", "NEW-012", "Home", 119.0, 6),
    ("Gel Pens 10-pack", "NEW-013", "Office", 22.9, 30),
    ("Sticky Notes", "NEW-014", "Office", 8.9, 60),
    ("Stapler", "NEW-015", "Office", 27.9, 12),
    ("Whiteboard Markers", "NEW-016", "Office", 18.9, 20),
]


class ApiClient:
    """Minimal JSON client for the inventory API (standard library only)."""

    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")

    def request(self, method, path, payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(self.base_url + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                return res.status, json.loads(res.read() or b"{}")
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read() or b"{}")

    def get(self, path):
        return self.request("GET", path)

    def post(self, path, payload):
        return self.request("POST", path, payload)


def run_sales(api, rng):
    """A few customers buy random in-stock items; sold-out items sometimes get a delivery."""
    status, products = api.get("/api/products")
    if status != 200:
        raise RuntimeError(f"Could not list products (HTTP {status})")

    log = []
    in_stock = [p for p in products if p["stock"] > 0]
    for product in rng.sample(in_stock, k=min(len(in_stock), rng.randint(3, 6))):
        quantity = rng.randint(1, min(3, product["stock"]))
        status, _ = api.post(f"/api/products/{product['id']}/sell", {"quantity": quantity})
        if status == 200:
            log.append(f"sold {quantity} x {product['name']} ({product['store']})")

    # A supplier occasionally delivers sold-out items, so the store never empties completely.
    for product in (p for p in products if p["stock"] == 0):
        if rng.random() < 0.25:
            quantity = max(product["suggested_reorder"], 1)
            status, _ = api.post(f"/api/products/{product['id']}/restock",
                                 {"quantity": quantity, "note": "supplier delivery (simulator)"})
            if status == 200:
                log.append(f"delivered {quantity} x {product['name']} ({product['store']})")
    return log


def run_new_product(api, rng):
    """Add the next catalog product that does not exist yet. Returns its SKU, or None."""
    status, products = api.get("/api/products")
    if status != 200:
        raise RuntimeError(f"Could not list products (HTTP {status})")
    existing = {p["sku"] for p in products}

    for name, sku, category, price, min_stock in CATALOG:
        if sku in existing:
            continue
        payload = {"name": name, "sku": sku, "category": category, "price": price,
                   "min_stock": min_stock, "store": rng.choice(STORES),
                   "stock": rng.randint(min_stock, min_stock * 4)}
        status, body = api.post("/api/products", payload)
        if status != 201:
            raise RuntimeError(f"Could not add {sku}: {body.get('error', status)}")
        return sku
    return None


def main(argv):
    if len(argv) != 2 or argv[1] not in ("sales", "new-product"):
        print(__doc__)
        return 2
    api = ApiClient(os.environ.get("SIM_API_URL", "http://backend:5000"))
    status, body = api.get("/api/simulation")
    if status == 200 and not body.get("enabled", True):
        print("simulation paused from the dashboard - nothing to do")
        return 0
    rng = random.Random()
    if argv[1] == "sales":
        for line in run_sales(api, rng) or ["nothing to sell"]:
            print(line)
    else:
        sku = run_new_product(api, rng)
        print(f"new product launched: {sku}" if sku else "catalog complete - no new products")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
