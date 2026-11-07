"""
Tests for the store simulator. The simulator normally calls the API over HTTP;
here it talks to the Flask test client through a small adapter, so no server is needed.
"""
import os
import random
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
import simulator  # noqa: E402


class FlaskClientApi:
    """Same interface as simulator.ApiClient, backed by Flask's test client."""

    def __init__(self, client):
        self.client = client

    def get(self, path):
        res = self.client.get(path)
        return res.status_code, res.get_json()

    def post(self, path, payload):
        res = self.client.post(path, json=payload)
        return res.status_code, res.get_json()


@pytest.fixture
def api(tmp_path):
    app = create_app({"TESTING": True, "DATABASE_URL": f"sqlite:///{tmp_path / 'sim.db'}", "SEED_DATA": True})
    return FlaskClientApi(app.test_client())


def test_sales_reduce_stock(api):
    log = simulator.run_sales(api, random.Random(1))
    sold = [line for line in log if line.startswith("sold")]
    assert 3 <= len(sold) <= 6
    assert api.get("/api/products/analytics")[1]["units_sold_today"] > 0


def test_new_products_follow_catalog_and_stop(api):
    first = simulator.run_new_product(api, random.Random(1))
    assert first == simulator.CATALOG[0][1]
    for _ in range(len(simulator.CATALOG) - 1):
        assert simulator.run_new_product(api, random.Random(1)) is not None
    assert simulator.run_new_product(api, random.Random(1)) is None  # catalog complete


def test_cli_rejects_unknown_command(capsys):
    assert simulator.main(["simulator.py", "bogus"]) == 2


def test_paused_simulator_does_nothing(api, monkeypatch, capsys):
    api.client.put("/api/simulation", json={"enabled": False})
    monkeypatch.setattr(simulator, "ApiClient", lambda url: api)
    before = api.get("/api/products/analytics")[1]["units_sold_today"]
    assert simulator.main(["simulator.py", "sales"]) == 0
    assert "paused" in capsys.readouterr().out
    assert api.get("/api/products/analytics")[1]["units_sold_today"] == before
