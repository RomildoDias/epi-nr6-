def test_list_colaboradores(client, admin_headers):
    r = client.get("/api/colaboradores", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_create_colaborador(client, admin_headers):
    r = client.get("/api/tenants", headers=admin_headers)
    tid = r.json()[0]["id"]

    r = client.post("/api/colaboradores", json={
        "nome": "Joao Teste",
        "matricula": "JT001",
        "setor": "Producao",
        "funcao": "Operador",
    }, params={"_tenant": tid}, headers=admin_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["nome"] == "Joao Teste"


def test_update_colaborador(client, admin_headers):
    r = client.get("/api/colaboradores", headers=admin_headers)
    colab = r.json()[0]

    r = client.put(f"/api/colaboradores/{colab['id']}", json={
        "funcao": "Tecnico Atualizado",
    }, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["funcao"] == "Tecnico Atualizado"


def test_tenant_isolation_colaborador(client, admin_headers, user_headers):
    r = client.get("/api/tenants", headers=admin_headers)
    ts = [t for t in r.json() if t["estado_uf"] == "TS"]

    r = client.post("/api/colaboradores", json={
        "nome": "Colab TS",
        "matricula": "TS002",
        "setor": "Producao",
        "funcao": "Operador",
    }, params={"_tenant": ts[0]["id"]}, headers=admin_headers)
    ts_id = r.json()["id"]

    r = client.get(f"/api/colaboradores/{ts_id}", headers=user_headers)
    assert r.status_code == 404
