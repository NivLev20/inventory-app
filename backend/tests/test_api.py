"""
Unit tests for the inventory API.
They use a temporary SQLite file, so no PostgreSQL is needed in the CI pipeline.
Run with:  pytest -v
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402


@pytest.fixture
def client(tmp_path):
    app = create_app({
        "TESTING": True,
        "DATABASE_URL": f"sqlite:///{tmp_path / 'test.db'}",
        "SEED_DATA": False,
    })
    return app.test_client()


@pytest.fixture
def seeded_client(tmp_path):
    app = create_app({
        "TESTING": True,
        "DATABASE_URL": f"sqlite:///{tmp_path / 'seed.db'}",
        "SEED_DATA": True,
    })
    return app.test_client()


def add(client, **overrides):
    payload = {"name": "Mouse", "sku": "SKU-1", "stock": 20, "min_stock": 5, "price": 10}
    payload.update(overrides)
    return client.post("/api/products", json=payload)


# ---------- health

def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


def test_ready(client):
    assert client.get("/ready").status_code == 200


# ---------- CRUD

def test_create_and_get_product(client):
    res = add(client)
    assert res.status_code == 201
    product = res.get_json()
    assert product["sku"] == "SKU-1"
    assert product["status"] == "OK"

    res = client.get(f"/api/products/{product['id']}")
    assert res.status_code == 200
    assert res.get_json()["name"] == "Mouse"


def test_list_products(client):
    add(client, sku="A")
    add(client, sku="B", store="Haifa")
    assert len(client.get("/api/products").get_json()) == 2
    assert len(client.get("/api/products?store=haifa").get_json()) == 1


def test_create_requires_name_and_sku(client):
    res = client.post("/api/products", json={"name": "No SKU"})
    assert res.status_code == 400
    assert "sku" in res.get_json()["error"]


def test_create_rejects_negative_stock(client):
    assert add(client, stock=-3).status_code == 400


def test_duplicate_sku_rejected(client):
    add(client)
    assert add(client).status_code == 409


def test_update_product(client):
    pid = add(client).get_json()["id"]
    res = client.put(f"/api/products/{pid}", json={"stock": 3, "price": 12.5})
    assert res.status_code == 200
    body = res.get_json()
    assert body["stock"] == 3
    assert body["price"] == 12.5
    assert body["status"] == "LOW"


def test_update_missing_product(client):
    assert client.put("/api/products/999", json={"stock": 1}).status_code == 404


def test_delete_product(client):
    pid = add(client).get_json()["id"]
    assert client.delete(f"/api/products/{pid}").status_code == 200
    assert client.get(f"/api/products/{pid}").status_code == 404


# ---------- restock

def test_restock_adds_stock_and_logs(client):
    pid = add(client, stock=2).get_json()["id"]
    res = client.post(f"/api/products/{pid}/restock", json={"quantity": 30, "note": "supplier"})
    assert res.status_code == 200
    assert res.get_json()["stock"] == 32

    logs = client.get("/api/restocks").get_json()
    assert len(logs) == 1
    assert logs[0]["stock_before"] == 2
    assert logs[0]["stock_after"] == 32
    assert logs[0]["product_name"] == "Mouse"


def test_restock_requires_positive_quantity(client):
    pid = add(client).get_json()["id"]
    assert client.post(f"/api/products/{pid}/restock", json={"quantity": 0}).status_code == 400
    assert client.post(f"/api/products/{pid}/restock", json={}).status_code == 400


# ---------- smart features / analytics

def test_low_stock_and_suggestion(client):
    add(client, sku="OK", stock=50, min_stock=5)
    add(client, sku="LOW", stock=3, min_stock=10)
    add(client, sku="OUT", stock=0, min_stock=10)
    low = client.get("/api/products/low-stock").get_json()
    assert [p["sku"] for p in low] == ["OUT", "LOW"]
    assert low[0]["status"] == "OUT"
    assert low[0]["suggested_reorder"] == 20  # 2 x min_stock - stock


def test_analytics(client):
    add(client, sku="A", stock=10, min_stock=2, price=5, category="Home")
    add(client, sku="B", stock=0, min_stock=2, price=5, category="Home")
    data = client.get("/api/products/analytics").get_json()
    assert data["total_products"] == 2
    assert data["total_units"] == 10
    assert data["inventory_value"] == 50
    assert data["by_status"] == {"OK": 1, "LOW": 0, "OUT": 1}
    assert data["by_category"]["Home"] == 10
    assert len(data["stock_trend"]) == 14
    assert data["stock_trend"][-1]["total_units"] == 10


def test_seed_data_loads(seeded_client):
    data = seeded_client.get("/api/products/analytics").get_json()
    assert data["total_products"] == 12
    assert data["by_status"]["OUT"] >= 1
    # Today's trend point matches the real current stock total
    assert data["stock_trend"][-1]["total_units"] == data["total_units"]


# ---------- sales

def test_sell_decreases_stock(client):
    pid = add(client, stock=10).get_json()["id"]
    res = client.post(f"/api/products/{pid}/sell", json={"quantity": 4})
    assert res.status_code == 200
    assert res.get_json()["stock"] == 6
    data = client.get("/api/products/analytics").get_json()
    assert data["units_sold_today"] == 4
    assert data["sales_trend"][-1]["units"] == 4


def test_cannot_sell_more_than_stock(client):
    pid = add(client, stock=2).get_json()["id"]
    res = client.post(f"/api/products/{pid}/sell", json={"quantity": 5})
    assert res.status_code == 409
    assert client.get(f"/api/products/{pid}").get_json()["stock"] == 2


# ---------- API docs

def test_openapi_and_docs(client):
    spec = client.get("/api/openapi.json").get_json()
    assert spec["openapi"].startswith("3.")
    assert "/api/products/{product_id}/sell" in spec["paths"]
    res = client.get("/api/docs")
    assert res.status_code == 200
    assert b"swagger-ui" in res.data


# ---------- simulator control

def test_simulation_toggle(client):
    assert client.get("/api/simulation").get_json() == {"enabled": True}
    assert client.put("/api/simulation", json={"enabled": False}).status_code == 200
    assert client.get("/api/simulation").get_json() == {"enabled": False}
    assert client.put("/api/simulation", json={"enabled": "no"}).status_code == 400


def test_rush_hour_sells_stock(client):
    add(client, sku="A", stock=50)
    add(client, sku="B", stock=50)
    result = client.post("/api/simulation/rush").get_json()
    assert result["sales"] == 20
    remaining = sum(p["stock"] for p in client.get("/api/products").get_json())
    assert remaining == 100 - result["units"]


def test_rush_hour_with_empty_store(client):
    add(client, sku="EMPTY", stock=0)
    assert client.post("/api/simulation/rush").get_json() == {"sales": 0, "units": 0}


# ---------- data integrity

def test_rejected_sale_leaves_no_trace(client):
    pid = add(client, stock=2).get_json()["id"]
    client.post(f"/api/products/{pid}/sell", json={"quantity": 5})
    assert client.get("/api/products/analytics").get_json()["units_sold_today"] == 0
    assert client.get(f"/api/products/{pid}").get_json()["stock"] == 2


def test_restock_log_records_before_and_after(client):
    pid = add(client, stock=4).get_json()["id"]
    client.post(f"/api/products/{pid}/sell", json={"quantity": 1})
    client.post(f"/api/products/{pid}/restock", json={"quantity": 10})
    log = client.get("/api/restocks").get_json()[0]
    assert (log["stock_before"], log["stock_after"]) == (3, 13)


@pytest.mark.parametrize("payload", [
    {"stock": 5.9}, {"stock": True}, {"stock": "abc"}, {"price": float("nan")},
    {"price": 10 ** 9}, {"min_stock": -1},
])
def test_invalid_numbers_rejected(client, payload):
    assert add(client, **payload).status_code == 400


def test_delete_removes_related_rows(client):
    pid = add(client, stock=10).get_json()["id"]
    client.post(f"/api/products/{pid}/sell", json={"quantity": 2})
    client.post(f"/api/products/{pid}/restock", json={"quantity": 3})
    assert client.delete(f"/api/products/{pid}").status_code == 200
    assert client.get("/api/restocks").get_json() == []
    assert client.get("/api/products/analytics").get_json()["units_sold_today"] == 0
