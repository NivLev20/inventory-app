"""
Demo data so the dashboard looks alive on first start.
Runs only when SEED_DATA=true and the products table is empty.
It also creates 14 days of fake stock history so the trend charts have data.
"""
import random
from datetime import datetime, timedelta, timezone

import db

PRODUCTS = [
    # name, sku, category, store, price, stock, min_stock
    ("Wireless Mouse", "ELC-001", "Electronics", "Tel Aviv", 89.90, 42, 15),
    ("USB-C Charger 65W", "ELC-002", "Electronics", "Tel Aviv", 149.00, 6, 10),
    ("HDMI Cable 2m", "ELC-003", "Electronics", "Haifa", 39.90, 0, 20),
    ("Mechanical Keyboard", "ELC-004", "Electronics", "Jerusalem", 349.00, 18, 8),
    ("Bluetooth Speaker", "ELC-005", "Electronics", "Haifa", 199.00, 9, 12),
    ("Olive Oil 1L", "GRC-001", "Grocery", "Tel Aviv", 44.90, 120, 40),
    ("Coffee Beans 500g", "GRC-002", "Grocery", "Jerusalem", 59.90, 14, 25),
    ("Pasta 500g", "GRC-003", "Grocery", "Haifa", 7.90, 300, 100),
    ("Dish Soap", "HOM-001", "Home", "Tel Aviv", 12.90, 75, 30),
    ("LED Bulb 10W", "HOM-002", "Home", "Jerusalem", 15.00, 3, 25),
    ("Bath Towel", "HOM-003", "Home", "Haifa", 49.90, 33, 10),
    ("Notebook A4", "OFC-001", "Office", "Jerusalem", 9.90, 210, 50),
]


def seed_if_empty():
    if db.query_one("SELECT id FROM products LIMIT 1"):
        return
    rng = random.Random(42)  # fixed seed -> same demo data every time
    now = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
    start = now - timedelta(days=13)

    for name, sku, category, store, price, stock, min_stock in PRODUCTS:
        product_id = db.execute(
            "INSERT INTO products (name, sku, category, store, price, stock, min_stock, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (name, sku, category, store, price, stock, min_stock,
             start.isoformat(), now.isoformat()),
            returning_id=True,
        )
        # Build 14 daily stock levels that end at today's real stock.
        # Going back in time, stock was usually higher (items were sold since).
        levels = [stock]
        for _ in range(13):
            levels.append(max(levels[-1] + rng.randint(-2, 6), 0))
        levels.reverse()  # oldest first, last value == current stock
        for day, value in enumerate(levels):
            ts = start + timedelta(days=day)
            db.execute(
                "INSERT INTO stock_history (product_id, stock, reason, created_at) VALUES (?, ?, ?, ?)",
                (product_id, value, "seed", min(ts, now).isoformat()),
            )

        if rng.random() < 0.6:
            qty = rng.choice([10, 20, 25, 50])
            when = now - timedelta(days=rng.randint(1, 12))
            db.execute(
                "INSERT INTO restock_logs (product_id, quantity, stock_before, stock_after, note, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (product_id, qty, max(stock - qty, 0), stock, "demo restock", when.isoformat()),
            )
