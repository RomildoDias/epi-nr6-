def test_list_colaboradores(client, admin_headers):
    r = client.get("/api/colaboradores", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_create_colaborador_without_consent(client, admin_headers):
    r = client.get("/api/tenants", headers=admin_headers)
    tid = r.json()[0]["id"]

    r = client.post("/api/colaboradores", json={
        "nome": "Sem Consentimento",
        "matricula": "SC001",
        "setor": "Teste",
        "funcao": "Teste",
        "consentimento_dados": False,
    }, params={"_tenant": tid}, headers=admin_headers)
    assert r.status_code == 400
    assert "consentir" in r.json()["detail"]


def test_create_colaborador_with_consent(client, admin_headers):
    r = client.get("/api/tenants", headers=admin_headers)
    tid = r.json()[0]["id"]

    r = client.post("/api/colaboradores", json={
        "nome": "Joao Consentimento",
        "matricula": "JC001",
        "setor": "Producao",
        "funcao": "Operador",
        "consentimento_dados": True,
    }, params={"_tenant": tid}, headers=admin_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["consentimento_dados"] == True
    assert data["data_consentimento"] is not None
    assert data["nome"] == "Joao Consentimento"


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
        "consentimento_dados": True,
    }, params={"_tenant": ts[0]["id"]}, headers=admin_headers)
    ts_id = r.json()["id"]

    r = client.get(f"/api/colaboradores/{ts_id}", headers=user_headers)
    assert r.status_code == 404


def test_dados_pessoais_export(client, admin_headers):
    r = client.get("/api/colaboradores", headers=admin_headers)
    colab = r.json()[0]

    r = client.get(f"/api/colaboradores/{colab['id']}/dados-pessoais", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["nome"] == colab["nome"]
    assert data["consentimento_dados"] == True
    assert "quant_entregas_realizadas" in data


def test_dados_pessoais_correction(client, admin_headers):
    r = client.get("/api/colaboradores", headers=admin_headers)
    colab = r.json()[0]

    r = client.put(f"/api/colaboradores/{colab['id']}/dados-pessoais", json={
        "nome": "Nome Corrigido",
    }, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["nome"] == "Nome Corrigido"
