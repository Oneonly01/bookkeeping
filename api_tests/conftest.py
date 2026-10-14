import os
import uuid
from decimal import Decimal

import pytest

from client import ApiClient


def _required(name):
    value = os.getenv(name)
    if not value:
        pytest.skip(f"set {name} to run API integration tests")
    return value


@pytest.fixture(scope="session")
def base_url():
    return _required("API_BASE_URL")


@pytest.fixture(scope="session")
def anonymous(base_url):
    return ApiClient(base_url)


@pytest.fixture(scope="session")
def api(anonymous, base_url):
    credentials = {
        "username": _required("API_TEST_USERNAME"),
        "password": _required("API_TEST_PASSWORD"),
    }
    data = anonymous.ok("POST", "/api/v1/auth/login/", json=credentials)
    assert data["access_token"]
    return ApiClient(base_url, data["access_token"])


@pytest.fixture
def resources(api):
    created = {"transactions": [], "accounts": [], "categories": []}
    yield created
    for transaction_id in reversed(created["transactions"]):
        response, _ = api.request("DELETE", f"/api/v1/transactions/{transaction_id}/")
        assert response.status_code in (200, 400), f"cleanup transaction {transaction_id}: {response.status_code}"
    for account_id in reversed(created["accounts"]):
        # Account deletion requires a zero balance. These accounts belong only to this test run.
        account = api.ok("GET", f"/api/v1/accounts/{account_id}/")
        if Decimal(str(account["balance"])) != Decimal("0.00"):
            api.ok("POST", f"/api/v1/accounts/{account_id}/adjust-balance/", json={"balance": "0.00", "note": "API test cleanup"})
        api.ok("DELETE", f"/api/v1/accounts/{account_id}/")
    for category_id in reversed(created["categories"]):
        api.ok("DELETE", f"/api/v1/categories/{category_id}/")


@pytest.fixture
def make_resources(api, resources):
    def make(kind):
        suffix = uuid.uuid4().hex[:10]
        account = api.ok("POST", "/api/v1/accounts/", json={
            "name": f"autotest-{suffix}", "account_type": "cash", "initial_balance": "0.00"
        })
        resources["accounts"].append(account["id"])
        category = api.ok("POST", "/api/v1/categories/", json={
            "name": f"autotest-{kind}-{suffix}", "category_type": kind
        })
        resources["categories"].append(category["id"])
        return account["id"], category["id"]
    return make
