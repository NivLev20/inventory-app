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
    POST   /api/products/<id>/sell           record a sale (JSON: quantity)
    GET    /api/simulation                   is the store simulator running?
    PUT    /api/simulation                   pause / resume it (JSON: enabled)
    POST   /api/simulation/rush              rush hour: ~20 purchases right now
    GET    /api/docs                         interactive API documentation (Swagger UI)
    GET    /health                           liveness probe (app is running)
    GET    /ready                            readiness probe (database reachable)
    GET    /metrics                          Prometheus metrics
"""
import math
import os
import random
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from flask import Flask, Response, jsonify, request

import db
from openapi import DOCS_HTML, SPEC

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


MAX_PRICE = 99_999_999.99  # NUMERIC(10, 2)
MAX_QUANTITY = 1_000_000


def parse_int(value, field, minimum=0):
    whole = isinstance(value, int) or (isinstance(value, float) and value.is_integer()) \
        or (isinstance(value, str) and value.strip().lstrip("-").isdigit())
    if isinstance(value, bool) or not whole:
        raise ValueError(f"'{field}' must be a whole number")
    number = int(value)
    if number < minimum or number > MAX_QUANTITY:
        raise ValueError(f"'{field}' must be between {minimum} and {MAX_QUANTITY}")
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
                price = float(value)
            except (TypeError, ValueError):
                raise ValueError("'price' must be a number")
            if isinstance(value, bool) or not math.isfinite(price) or not 0 <= price <= MAX_PRICE:
                raise ValueError(f"'price' must be between 0 and {MAX_PRICE}")
            clean[field] = round(price, 2)
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


def sell_product(product_id, quantity):
    """Take stock atomically. Returns the new stock level, or None if there was not enough.

    The check and the decrement are one conditional UPDATE, so two concurrent sales
    (replicas, CronJobs, rush hour) can neither oversell nor overwrite each other.
    """
    ts = now()
    with db.transaction():
        row = db.query_one(
            "UPDATE products SET stock = stock - ?, updated_at = ? "
            "WHERE id = ? AND stock >= ? RETURNING stock",
            (quantity, ts, product_id, quantity),
        )
        if row is None:
            return None
        db.execute("INSERT INTO sales (product_id, quantity, created_at) VALUES (?, ?, ?)",
                   (product_id, quantity, ts))
        record_history(product_id, row["stock"], "sale")
    return row["stock"]


def simulation_enabled():
    return db.get_setting("simulation_enabled", "true") == "true"


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
        except Exception:
            app.logger.warning("Readiness check failed", exc_info=True)
            return jsonify({"status": "not ready"}), 503
        return jsonify({"status": "ready"})

    # ---------- API documentation (Swagger)

    @app.get("/api/openapi.json")
    def openapi_spec():
        return jsonify(SPEC)

    @app.get("/api/docs")
    def api_docs():
        return Response(DOCS_HTML, mimetype="text/html")

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
        try:
            with db.transaction():
                new_id = db.execute(
                    "INSERT INTO products (name, sku, category, store, price, stock, min_stock, "
                    "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (data["name"], data["sku"], data["category"], data["store"], data["price"],
                     data["stock"], data["min_stock"], ts, ts),
                    returning_id=True,
                )
                record_history(new_id, data["stock"], "created")
        except Exception as exc:
            if db.is_integrity_error(exc):  # same SKU created concurrently
                return error(f"SKU '{data['sku']}' already exists", 409)
            raise
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
        columns = ", ".join(f"{field} = ?" for field in data)  # names come from ALLOWED_FIELDS only
        try:
            with db.transaction():
                db.execute(
                    f"UPDATE products SET {columns}, updated_at = ? WHERE id = ?",
                    (*data.values(), now(), product_id),
                )
                if "stock" in data and data["stock"] != product["stock"]:
                    record_history(product_id, data["stock"], "manual update")
        except Exception as exc:
            if db.is_integrity_error(exc):
                return error(f"SKU '{data['sku']}' already exists", 409)
            raise
        return jsonify(enrich(get_product(product_id)))

    @app.delete("/api/products/<int:product_id>")
    def delete_product(product_id):
        if not get_product(product_id):
            return error("Product not found", 404)
        # History, restock logs and sales go with it (ON DELETE CASCADE)
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
        note = str(data.get("note", "")).strip()[:200] or None
        ts = now()
        with db.transaction():
            # Relative update: concurrent sales and restocks never overwrite each other
            after = db.query_one(
                "UPDATE products SET stock = stock + ?, updated_at = ? WHERE id = ? RETURNING stock",
                (quantity, ts, product_id),
            )["stock"]
            db.execute(
                "INSERT INTO restock_logs (product_id, quantity, stock_before, stock_after, note, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (product_id, quantity, after - quantity, after, note, ts),
            )
            record_history(product_id, after, "restock")
        return jsonify(enrich(get_product(product_id)))

    # ---------- sales

    @app.post("/api/products/<int:product_id>/sell")
    def sell(product_id):
        product = get_product(product_id)
        if not product:
            return error("Product not found", 404)
        data = request.get_json(silent=True) or {}
        try:
            quantity = parse_int(data.get("quantity"), "quantity", minimum=1)
        except ValueError as exc:
            return error(str(exc), 400)
        if sell_product(product_id, quantity) is None:
            return error(f"Only {get_product(product_id)['stock']} units in stock", 409)
        return jsonify(enrich(get_product(product_id)))

    # ---------- simulator control

    @app.get("/api/simulation")
    def simulation_status():
        return jsonify({"enabled": simulation_enabled()})

    @app.put("/api/simulation")
    def simulation_update():
        data = request.get_json(silent=True) or {}
        if not isinstance(data.get("enabled"), bool):
            return error("'enabled' must be true or false", 400)
        db.set_setting("simulation_enabled", "true" if data["enabled"] else "false")
        return jsonify({"enabled": data["enabled"]})

    @app.post("/api/simulation/rush")
    def simulation_rush():
        """Rush hour: up to 20 random purchases right now, independent of the CronJobs."""
        rng = random.Random()
        sales = units = 0
        for _ in range(20):
            in_stock = db.query_all("SELECT * FROM products WHERE stock > 0")
            if not in_stock:
                break
            product = rng.choice(in_stock)
            quantity = rng.randint(1, min(5, product["stock"]))
            if sell_product(product["id"], quantity) is not None:
                sales += 1
                units += quantity
        return jsonify({"sales": sales, "units": units})

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
        # Only the requested window is read: a baseline (last level per product before it)
        # plus the rows inside it, so the cost does not grow with the age of the system.
        today = datetime.fromisoformat(now()).date()
        start = today - timedelta(days=days - 1)
        since = start.isoformat()
        latest = {r["product_id"]: r["stock"] for r in db.query_all(
            "SELECT product_id, stock FROM stock_history WHERE id IN "
            "(SELECT MAX(id) FROM stock_history WHERE created_at < ? GROUP BY product_id)", (since,))}
        history = db.query_all(
            "SELECT product_id, stock, created_at FROM stock_history WHERE created_at >= ? ORDER BY created_at, id",
            (since,))
        alive = {p["id"] for p in products}
        trend = []
        index = 0
        for offset in range(days):
            day = (start + timedelta(days=offset)).isoformat()
            while index < len(history) and history[index]["created_at"][:10] <= day:
                latest[history[index]["product_id"]] = history[index]["stock"]
                index += 1
            trend.append({"date": day, "total_units": sum(v for k, v in latest.items() if k in alive)})

        def units_per_day(table):
            day = db.day_of("created_at")
            rows = db.query_all(
                f"SELECT {day} AS day, SUM(quantity) AS units FROM {table} WHERE created_at >= ? GROUP BY {day}",
                (since,))
            return {r["day"]: int(r["units"]) for r in rows}

        restocks_per_day = units_per_day("restock_logs")
        sales_per_day = units_per_day("sales")

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
            "sales_trend": [
                {"date": t["date"], "units": sales_per_day.get(t["date"], 0)} for t in trend
            ],
            "units_sold_today": sales_per_day.get(today.isoformat(), 0),
        })


class InventoryCollector:
    """Business metrics, computed once per Prometheus scrape (one database round trip).

    If the database is unreachable the metrics are simply absent for that scrape,
    so graphs show a gap instead of a misleading value.
    """

    def __init__(self, app):
        self.app = app

    def collect(self):
        from prometheus_client.core import GaugeMetricFamily
        try:
            with self.app.app_context():
                products = [enrich(p) for p in db.query_all("SELECT * FROM products")]
                sold = db.query_one("SELECT COALESCE(SUM(quantity), 0) AS units FROM sales WHERE created_at >= ?",
                                    (now()[:10],))["units"]
        except Exception:
            self.app.logger.warning("Inventory metrics unavailable", exc_info=True)
            return
        values = [
            ("inventory_products_total", "Number of products", len(products)),
            ("inventory_units_total", "Total units in stock", sum(p["stock"] for p in products)),
            ("inventory_low_stock_products", "Products at or below their minimum, not sold out",
             sum(p["status"] == "LOW" for p in products)),
            ("inventory_out_of_stock_products", "Products with zero stock",
             sum(p["status"] == "OUT" for p in products)),
            ("inventory_value", "Total inventory value", sum(p["stock_value"] for p in products)),
            ("inventory_units_sold_today", "Units sold since midnight (UTC)", float(sold)),
        ]
        for name, description, value in values:
            yield GaugeMetricFamily(name, description, value=value)


def register_metrics(app):
    """Expose /metrics for Prometheus: request latency/count + inventory gauges."""
    if app.config.get("TESTING"):
        return
    try:
        from prometheus_flask_exporter import PrometheusMetrics
    except ImportError:  # library not installed (e.g. a minimal local run)
        app.logger.warning("prometheus_flask_exporter not installed - /metrics disabled")
        return

    metrics = PrometheusMetrics(app, group_by="url_rule")
    metrics.info("inventory_app_info", "Inventory app info", env=app.config["APP_ENV"])

    from prometheus_client.core import REGISTRY
    REGISTRY.register(InventoryCollector(app))


if __name__ == "__main__":
    # Local run: python app.py   (in Docker we use gunicorn: "app:create_app()")
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
