import os

import pytest

from client import ApiClient


@pytest.fixture(scope="session")
def second_api(anonymous, base_url):
    username = os.getenv("API_TEST_USERNAME_2")
    password = os.getenv("API_TEST_PASSWORD_2")
    if not username or not password:
        pytest.skip("set API_TEST_USERNAME_2 and API_TEST_PASSWORD_2 for cross-user tests")
    data = anonymous.ok("POST", "/api/v1/auth/login/", json={"username": username, "password": password})
    return ApiClient(base_url, data["access_token"])


@pytest.mark.negative
def test_other_user_cannot_read_or_delete_account(api, second_api, make_resources):
    account_id, _ = make_resources("expense")
    second_api.error("GET", f"/api/v1/accounts/{account_id}/", 400)
    second_api.error("DELETE", f"/api/v1/accounts/{account_id}/", 400)
    assert api.ok("GET", f"/api/v1/accounts/{account_id}/")["id"] == account_id


@pytest.mark.negative
def test_other_user_cannot_create_transaction_on_foreign_account(api, second_api, make_resources):
    account_id, category_id = make_resources("expense")
    second_api.error("POST", "/api/v1/transactions/", 400, json={
        "account_id": account_id,
        "category_id": category_id,
        "transaction_type": "expense",
        "amount": "1.00",
        "transaction_time": "2026-10-12T12:00:00+08:00",
    })
    assert api.ok("GET", f"/api/v1/accounts/{account_id}/")["balance"] == "0.00"
