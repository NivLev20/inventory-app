"""
Smart Retail Inventory - Flask REST API

Endpoints (from the course project #1 spec, plus health/metrics):
    GET    /api/products                     list products (filters: ?store=&status=)
    GET    /api/products/<id>                one product
    POST   /api/products                     create product
    PUT    /api/products/<id>                update product / stock
    DELETE /api/products/<id>                delete product
    POST   /api/products/<id>/restock        add stock (JSON: quantity, note)
    GET    /api/restocks                     restock history
    GET    /api/products/low-stock           products at or below their minimum
    GET    /api/products/analytics           numbers + trends for the dashboard
    GET    /health                           liveness probe (app is running)
    GET    /ready                            readiness probe (database reachable)
    GET    /metrics                          Prometheus metrics
"""
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from flask import Flask, jsonify, request

import db

ALLOWED_FIELDS = ("name", "sku", "category", "store", "price", "stock", "min_stock")


def now():
    """Current UTC time as text, e.g. 2026-11-07T14:30:00 (works in SQLite and PostgreSQL)."""
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0).isoformat()


# ---------------------------------------------------------------- helpers

def stock_status(product):
    if product["stock"] <= 0:
        return "OUT"
    if product["stock"] <= product["min_stock"]:
        return "LOW"
    return "OK"


def enrich(product):
    """Add the 'smart' computed fields to a product row."""
    product["status"] = stock_status(product)
    # Suggest ordering enough to reach twice the minimum level.
    product["suggested_reorder"] = max(product["min_stock"] * 2 - product["stock"], 0)
    product["stock_value"] = round(float(product["price"]) * product["stock"], 2)
    return product


def error(message, code):
    return jsonify({"error": message}), code


def parse_int(value, field, minimum=0):
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"'{field}' must be a whole number")
    if isinstance(value, bool) or number < minimum:
        raise ValueError(f"'{field}' must be {minimum} or more")
    return number


def validate(data, partial=False):
    if not isinstance(data, dict):
        raise ValueError("Request body must be JSON")
    clean = {}
    for field in ALLOWED_FIELDS:
        if field not in data:
            continue
        value = data[field]
        if field in ("stock", "min_stock"):
            clean[field] = parse_int(value, field)
        elif field == "price":
            try:
                clean[field] = round(float(value), 2)
            except (TypeError, ValueError):
                raise ValueError("'price' must be a number")
            if clean[field] < 0:
                raise ValueError("'price' must be 0 or more")
        else:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"'{field}' must be a non-empty text")
            clean[field] = value.strip()
    if not partial:
        for required in ("name", "sku"):
            if required not in clean:
                raise ValueError(f"'{required}' is required")
    if not clean:
        raise ValueError("No valid fields to update")
    return clean


def get_product(product_id):
    return db.query_one("SELECT * FROM products WHERE id = ?", (product_id,))


def record_history(product_id, stock, reason):
    db.execute(
        "INSERT INTO stock_history (product_id, stock, reason, created_at) VALUES (?, ?, ?, ?)",
        (product_id, stock, reason, now()),
    )


# ---------------------------------------------------------------- app

def wait_for_database(app, attempts=30, delay=2):
    """On startup the database may still be booting (Docker / Kubernetes). Retry for ~1 minute."""
    for attempt in range(1, attempts + 1):
        try:
            db.ping()
            return
        except Exception as exc:
            db.close_db()
            if attempt == attempts:
                raise
            app.logger.warning("Database not ready (%s), retry %s/%s", exc, attempt, attempts)
            time.sleep(delay)


def create_app(config=None):
    app = Flask(__name__)
    app.config["DATABASE_URL"] = os.environ.get("DATABASE_URL", "sqlite:///inventory.db")
    app.config["APP_ENV"] = os.environ.get("APP_ENV", "development")
    app.config["SEED_DATA"] = os.environ.get("SEED_DATA", "false").lower() == "true"
    app.config.update(config or {})
    app.teardown_appcontext(db.close_db)

    with app.app_context():
        wait_for_database(app)
        # Several replicas may start at the same moment (Kubernetes runs 2 backends).
        # The lock makes them create tables / load demo data one after another, not together.
        with db.startup_lock():
            db.init_db()
            if app.config["SEED_DATA"]:
                from seed import seed_if_empty
                seed_if_empty()

    register_routes(app)
    register_metrics(app)
    return app


def register_routes(app):

    @app.errorhandler(404)
    def not_found(_e):
        return error("Not found", 404)

    @app.errorhandler(405)
    def not_allowed(_e):
        return error("Method not allowed", 405)

    # ---------- health

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "env": app.config["APP_ENV"]})

    @app.get("/ready")
    def ready():
        try:
            db.ping()
        except Exception as exc:  # database not reachable yet
            return jsonify({"status": "not ready", "error": str(exc)}), 503
        return jsonify({"status": "ready"})

    # ---------- products CRUD

    @app.get("/api/products")
    def list_products():
        products = [enrich(p) for p in db.query_all("SELECT * FROM products ORDER BY name")]
        store = request.args.get("store")
        status = request.args.get("status")
        if store:
            products = [p for p in products if p["store"].lower() == store.lower()]
        if status:
            products = [p for p in products if p["status"] == status.upper()]
        return jsonify(products)

    @app.get("/api/products/<int:product_id>")
    def product_details(product_id):
        product = get_product(product_id)
        if not product:
            return error("Product not found", 404)
        return jsonify(enrich(product))

    @app.post("/api/products")
    def create_product():
        try:
            data = validate(request.get_json(silent=True))
        except ValueError as exc:
            return error(str(exc), 400)
        if db.query_one("SELECT id FROM products WHERE sku = ?", (data["sku"],)):
            return error(f"SKU '{data['sku']}' already exists", 409)
        data.setdefault("category", "General")
        data.setdefault("store", "Main")
        data.setdefault("price", 0)
        data.setdefault("stock", 0)
        data.setdefault("min_stock", 10)
        ts = now()
        new_id = db.execute(
            "INSERT INTO products (name, sku, category, store, price, stock, min_stock, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (data["name"], data["sku"], data["category"], data["store"], data["price"],
             data["stock"], data["min_stock"], ts, ts),
            returning_id=True,
        )
        record_history(new_id, data["stock"], "created")
        return jsonify(enrich(get_product(new_id))), 201

    @app.put("/api/products/<int:product_id>")
    def update_product(product_id):
        product = get_product(product_id)
        if not product:
            return error("Product not found", 404)
        try:
            data = validate(request.get_json(silent=True), partial=True)
        except ValueError as exc:
            return error(str(exc), 400)
        if "sku" in data and data["sku"] != product["sku"]:
            if db.query_one("SELECT id FROM products WHERE sku = ?", (data["sku"],)):
                return error(f"SKU '{data['sku']}' already exists", 409)
        columns = ", ".join(f"{field} = ?" for field in data)
        db.execute(
            f"UPDATE products SET {columns}, updated_at = ? WHERE id = ?",
            (*data.values(), now(), product_id),
        )
        if "stock" in data and data["stock"] != product["stock"]:
            record_history(product_id, data["stock"], "manual update")
        return jsonify(enrich(get_product(product_id)))

    @app.delete("/api/products/<int:product_id>")
    def delete_product(product_id):
        if not get_product(product_id):
            return error("Product not found", 404)
        db.execute("DELETE FROM stock_history WHERE product_id = ?", (product_id,))
        db.execute("DELETE FROM restock_logs WHERE product_id = ?", (product_id,))
        db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        return jsonify({"deleted": product_id})

    # ---------- restocking

    @app.post("/api/products/<int:product_id>/restock")
    def restock(product_id):
        product = get_product(product_id)
        if not product:
            return error("Product not found", 404)
        data = request.get_json(silent=True) or {}
        try:
            quantity = parse_int(data.get("quantity"), "quantity", minimum=1)
        except ValueError as exc:
            return error(str(exc), 400)
        note = str(data.get("note", "")).strip() or None
        before = product["stock"]
        after = before + quantity
        ts = now()
        db.execute("UPDATE products SET stock = ?, updated_at = ? WHERE id = ?",
                   (after, ts, product_id))
        db.execute(
            "INSERT INTO restock_logs (product_id, quantity, stock_before, stock_after, note, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (product_id, quantity, before, after, note, ts),
        )
        record_history(product_id, after, "restock")
        return jsonify(enrich(get_product(product_id)))

    @app.get("/api/restocks")
    def restock_history():
        rows = db.query_all(
            "SELECT r.*, p.name AS product_name, p.sku, p.store FROM restock_logs r "
            "JOIN products p ON p.id = r.product_id ORDER BY r.created_at DESC, r.id DESC"
        )
        return jsonify(rows)

    # ---------- analytics

    @app.get("/api/products/low-stock")
    def low_stock():
        products = [enrich(p) for p in db.query_all("SELECT * FROM products")]
        low = [p for p in products if p["status"] in ("LOW", "OUT")]
        low.sort(key=lambda p: (p["stock"] - p["min_stock"], p["name"]))
        return jsonify(low)

    @app.get("/api/products/analytics")
    def analytics():
        days = min(max(request.args.get("days", 14, type=int), 1), 90)
        products = [enrich(p) for p in db.query_all("SELECT * FROM products")]

        by_status = {"OK": 0, "LOW": 0, "OUT": 0}
        by_category = defaultdict(int)
        by_store = defaultdict(lambda: {"products": 0, "units": 0, "low_or_out": 0})
        for p in products:
            by_status[p["status"]] += 1
            by_category[p["category"]] += p["stock"]
            store = by_store[p["store"]]
            store["products"] += 1
            store["units"] += p["stock"]
            store["low_or_out"] += p["status"] != "OK"

        # Stock trend: total units at the end of each day, rebuilt from history.
        history = db.query_all("SELECT product_id, stock, created_at FROM stock_history ORDER BY created_at, id")
        restocks = db.query_all("SELECT quantity, created_at FROM restock_logs")
        today = datetime.fromisoformat(now()).date()
        start = today - timedelta(days=days - 1)
        latest = {}
        trend = []
        index = 0
        for offset in range(days):
            day = start + timedelta(days=offset)
            while index < len(history) and history[index]["created_at"][:10] <= day.isoformat():
                latest[history[index]["product_id"]] = history[index]["stock"]
                index += 1
            alive = {p["id"] for p in products}
            trend.append({"date": day.isoformat(),
                          "total_units": sum(v for k, v in latest.items() if k in alive)})

        restocks_per_day = defaultdict(int)
        for r in restocks:
            restocks_per_day[r["created_at"][:10]] += r["quantity"]

        return jsonify({
            "total_products": len(products),
            "total_units": sum(p["stock"] for p in products),
            "inventory_value": round(sum(p["stock_value"] for p in products), 2),
            "by_status": by_status,
            "by_category": dict(by_category),
            "by_store": dict(by_store),
            "stock_trend": trend,
            "restocks_trend": [
                {"date": t["date"], "units": restocks_per_day.get(t["date"], 0)} for t in trend
            ],
        })


def register_metrics(app):
    """Expose /metrics for Prometheus: request latency/count + inventory gauges."""
    if app.config.get("TESTING"):
        return
    try:
        from prometheus_client import Gauge
        from prometheus_flask_exporter import PrometheusMetrics
    except ImportError:  # library not installed (e.g. a minimal local run)
        app.logger.warning("prometheus_flask_exporter not installed - /metrics disabled")
        return

    metrics = PrometheusMetrics(app, group_by="url_rule")
    metrics.info("inventory_app_info", "Inventory app info", env=app.config["APP_ENV"])

    def inventory_numbers():
        with app.app_context():
            products = [enrich(p) for p in db.query_all("SELECT * FROM products")]
        return products

    def safe(fn):
        def wrapper():
            try:
                return fn(inventory_numbers())
            except Exception:
                return -1
        return wrapper

    Gauge("inventory_products_total", "Number of products").set_function(
        safe(lambda ps: len(ps)))
    Gauge("inventory_units_total", "Total units in stock").set_function(
        safe(lambda ps: sum(p["stock"] for p in ps)))
    Gauge("inventory_low_stock_products", "Products at or below minimum stock").set_function(
        safe(lambda ps: sum(p["status"] == "LOW" for p in ps)))
    Gauge("inventory_out_of_stock_products", "Products with zero stock").set_function(
        safe(lambda ps: sum(p["status"] == "OUT" for p in ps)))
    Gauge("inventory_value", "Total inventory value").set_function(
        safe(lambda ps: sum(p["stock_value"] for p in ps)))


if __name__ == "__main__":
    # Local run: python app.py   (in Docker we use gunicorn: "app:create_app()")
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
