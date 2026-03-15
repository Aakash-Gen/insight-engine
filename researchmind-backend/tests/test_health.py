"""
Tests for GET /health — no auth required.
"""


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_response_shape(self, client):
        body = client.get("/health").json()
        assert body["status"] == "ok"
        assert "provider" in body
        assert "model" in body

    def test_health_provider_is_valid(self, client):
        provider = client.get("/health").json()["provider"]
        assert provider in ("groq", "anthropic", "xai")
