from datetime import date, timedelta


TODAY = date.today()


def test_list_epis(client, admin_headers):
    r = client.get("/api/epis", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_list_epis_with_tenant_filter(client, admin_headers):
    r = client.get("/api/tenants", headers=admin_headers)
    tfs = [t for t in r.json() if t["estado_uf"] == "TF"]
    tid = tfs[0]["id"]

    r = client.get(f"/api/epis?_tenant={tid}", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["nome"] == "Capacete Teste"


def test_list_epis_other_tenant_empty(client, admin_headers):
    r = client.get("/api/tenants", headers=admin_headers)
    ts = [t for t in r.json() if t["estado_uf"] == "TS"]
    tid = ts[0]["id"]

    r = client.get(f"/api/epis?_tenant={tid}", headers=admin_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_superadmin_without_tenant_filter(client, admin_headers):
    r = client.get("/api/epis", headers=admin_headers)
    data = r.json()
    assert len(data) >= 1


def test_create_epi(client, admin_headers):
    r = client.get("/api/tenants", headers=admin_headers)
    tid = r.json()[0]["id"]

    r = client.post("/api/epis", json={
        "nome": "Luva Teste",
        "ca": "99999",
        "fabricante": "Teste Ltda",
        "tipo_protecao": "Maos",
        "vida_util_dias": 180,
        "validade_ca": str(TODAY + timedelta(days=180)),
        "estoque_minimo": 5,
        "quantidade": 20,
    }, params={"_tenant": tid}, headers=admin_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["nome"] == "Luva Teste"
    assert data["quantidade"] == 20


def test_create_epi_with_expired_ca(client, admin_headers):
    r = client.get("/api/tenants", headers=admin_headers)
    tid = r.json()[0]["id"]

    r = client.post("/api/epis", json={
        "nome": "EPI Vencido",
        "ca": "88888",
        "fabricante": "Teste",
        "tipo_protecao": "Teste",
        "vida_util_dias": 365,
        "validade_ca": str(TODAY - timedelta(days=10)),
        "estoque_minimo": 5,
        "quantidade": 10,
    }, params={"_tenant": tid}, headers=admin_headers)
    assert r.status_code == 422


def test_update_epi(client, admin_headers):
    r = client.get("/api/epis", headers=admin_headers)
    epi = r.json()[0]

    r = client.put(f"/api/epis/{epi['id']}", json={
        "quantidade": 50,
    }, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["quantidade"] == 50


def test_inativar_epi(client, admin_headers):
    r = client.get("/api/epis", headers=admin_headers)
    epi = r.json()[0]

    r = client.delete(f"/api/epis/{epi['id']}", headers=admin_headers)
    assert r.status_code == 204

    r = client.get("/api/epis", headers=admin_headers)
    assert epi["id"] not in [e["id"] for e in r.json()]


def test_estoque_entrada(client, admin_headers):
    r = client.get("/api/tenants", headers=admin_headers)
    tid = r.json()[0]["id"]

    r = client.get("/api/epis", headers=admin_headers)
    epi_id = r.json()[0]["id"]

    r = client.post(f"/api/estoque/{epi_id}/entrada", json={
        "quantidade": 10,
        "motivo": "Compra NF 123",
        "documento_nf": "NF-12345",
    }, params={"_tenant": tid}, headers=admin_headers)
    assert r.status_code == 201 or r.status_code == 200


def test_tipos_protecao(client, admin_headers):
    r = client.get("/api/tipos-protecao", headers=admin_headers)
    assert r.status_code == 200
    assert "Impacto" in r.json()
