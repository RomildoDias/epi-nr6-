def test_login_success(client):
    r = client.post("/api/auth/login", json={"login": "admin", "senha": "admin123"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["perfil"] == "superadmin"
    assert data["precisa_trocar_senha"] == True


def test_login_wrong_password(client):
    r = client.post("/api/auth/login", json={"login": "admin", "senha": "wrong"})
    assert r.status_code == 401


def test_login_nonexistent_user(client):
    r = client.post("/api/auth/login", json={"login": "noone", "senha": "x"})
    assert r.status_code == 401


def test_login_rate_limited(client):
    from app.main import app
    app.state.limiter.enabled = True
    for _ in range(10):
        client.post("/api/auth/login", json={"login": "admin", "senha": "wrong"})
    r = client.post("/api/auth/login", json={"login": "admin", "senha": "wrong"})
    assert r.status_code == 429
    app.state.limiter.enabled = False


def test_login_tenant_user(client):
    r = client.post("/api/auth/login", json={"login": "admin.tf", "senha": "senha123"})
    assert r.status_code == 200
    data = r.json()
    assert data["tenant_id"] is not None
    assert data["tenant_nome"] == "Filial Teste 1"


def test_unauthenticated_access(client):
    r = client.get("/api/tenants")
    assert r.status_code == 401


def test_forbidden_permission(client, user_headers):
    r = client.get("/api/tenants", headers=user_headers)
    assert r.status_code == 403


def test_trocar_senha_min_length(client, admin_headers):
    r = client.post("/api/auth/trocar-senha", json={
        "senha_atual": "admin123",
        "nova_senha": "123",
    }, headers=admin_headers)
    assert r.status_code == 400
    assert "8" in r.json()["detail"]
