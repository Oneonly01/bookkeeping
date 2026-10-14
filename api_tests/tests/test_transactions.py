from datetime import datetime, timezone
from decimal import Decimal

import pytest


def amount(value):
    return Decimal(str(value))


def payload(account_id, category_id, kind, value):
    return {
        "account_id": account_id,
        "category_id": category_id,
        "transaction_type": kind,
        "amount": value,
        "transaction_time": datetime.now(timezone.utc).isoformat(),
    }


def balance(api, account_id):
    return amount(api.ok("GET", f"/api/v1/accounts/{account_id}/")["balance"])


@pytest.mark.smoke
def test_expense_update_delete_restores_balance(api, make_resources, resources):
    account_id, category_id = make_resources("expense")
    api.ok("POST", f"/api/v1/accounts/{account_id}/adjust-balance/", json={"balance": "100.00", "note": "API test setup"})
    assert balance(api, account_id) == Decimal("100.00")

    record = api.ok("POST", "/api/v1/transactions/", json=payload(account_id, category_id, "expense", "12.30"))
    transaction_id = record["id"]
    resources["transactions"].append(transaction_id)
    assert balance(api, account_id) == Decimal("87.70")
    assert amount(api.ok("GET", f"/api/v1/transactions/{transaction_id}/")["amount"]) == Decimal("12.30")

    updated = api.ok("PUT", f"/api/v1/transactions/{transaction_id}/", json={"amount": "20.00"})
    assert amount(updated["amount"]) == Decimal("20.00")
    assert balance(api, account_id) == Decimal("80.00")

    api.ok("DELETE", f"/api/v1/transactions/{transaction_id}/")
    resources["transactions"].remove(transaction_id)
    assert balance(api, account_id) == Decimal("100.00")
    api.error("GET", f"/api/v1/transactions/{transaction_id}/", 400)


@pytest.mark.negative
@pytest.mark.parametrize("invalid_amount", ["0.00", "-1.00", "1.001", "abc"])
def test_invalid_amount_does_not_change_balance(api, make_resources, invalid_amount):
    account_id, category_id = make_resources("expense")
    api.error("POST", "/api/v1/transactions/", 400, json=payload(account_id, category_id, "expense", invalid_amount))
    assert balance(api, account_id) == Decimal("0.00")


@pytest.mark.negative
def test_insufficient_balance_does_not_create_transaction(api, make_resources):
    account_id, category_id = make_resources("expense")
    api.error("POST", "/api/v1/transactions/", 400, json=payload(account_id, category_id, "expense", "0.01"))
    assert balance(api, account_id) == Decimal("0.00")


@pytest.mark.negative
def test_category_type_mismatch_does_not_change_balance(api, make_resources):
    account_id, income_category_id = make_resources("income")
    api.error("POST", "/api/v1/transactions/", 400, json=payload(account_id, income_category_id, "expense", "1.00"))
    assert balance(api, account_id) == Decimal("0.00")


@pytest.mark.negative
def test_invalid_summary_date_range(api):
    api.error("GET", "/api/v1/transactions/summary/", 400, params={"start_date": "2026-10-12", "end_date": "2026-10-11"})
