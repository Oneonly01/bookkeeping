import requests


class ApiClient:
    def __init__(self, base_url, token=None):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def request(self, method, path, **kwargs):
        kwargs.setdefault("timeout", 10)
        response = self.session.request(method, self.base_url + path, **kwargs)
        try:
            body = response.json()
        except ValueError as exc:
            raise AssertionError(f"{method} {path}: response is not JSON; HTTP {response.status_code}") from exc
        assert isinstance(body, dict), f"{method} {path}: response must be an object"
        assert {"code", "message", "data"} <= body.keys(), f"{method} {path}: invalid response envelope: {body}"
        return response, body

    def ok(self, method, path, **kwargs):
        response, body = self.request(method, path, **kwargs)
        assert response.status_code == 200, f"{method} {path}: HTTP {response.status_code}, {body}"
        assert body["code"] == 200, f"{method} {path}: {body}"
        return body["data"]

    def error(self, method, path, status, **kwargs):
        response, body = self.request(method, path, **kwargs)
        assert response.status_code == status, f"{method} {path}: HTTP {response.status_code}, {body}"
        assert body["code"] == status, f"{method} {path}: {body}"
        assert isinstance(body["message"], str) and body["message"]
        return body
