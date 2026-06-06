def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "usuarios" in data


def test_health_returns_users_count(client):
    r = client.get("/api/health")
    assert r.json()["usuarios"] >= 4


def test_frontend_is_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
