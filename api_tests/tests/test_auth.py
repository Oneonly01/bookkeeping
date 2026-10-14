import pytest

from client import ApiClient


@pytest.mark.smoke
def test_login_and_current_user(api):
    user = api.ok("GET", "/api/v1/users/me/")
    assert user["username"]


@pytest.mark.negative
@pytest.mark.parametrize("path", ["/api/v1/users/me/", "/api/v1/accounts/", "/api/v1/transactions/"])
def test_anonymous_access_is_rejected(anonymous, path):
    anonymous.error("GET", path, 401)


@pytest.mark.negative
def test_bad_password_is_rejected(anonymous):
    anonymous.error("POST", "/api/v1/auth/login/", 400, json={"username": "nonexistent-api-test-user", "password": "wrong-password"})


@pytest.mark.negative
def test_invalid_token_is_rejected(base_url):
    ApiClient(base_url, "invalid-token").error("GET", "/api/v1/users/me/", 401)
