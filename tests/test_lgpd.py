def test_privacidade_endpoint(client):
    r = client.get("/api/privacidade")
    assert r.status_code == 200
    data = r.json()
    assert "controlador" in data
    assert "finalidade" in data
    assert "direitos_titular" in data


def test_relatorio_retencao(client, admin_headers):
    r = client.get("/api/relatorio-retencao", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["periodo_retencao_dias"] == 1825
    assert "colaboradores" in data
    assert "entregas" in data


def test_purge_empty(client, admin_headers):
    r = client.post("/api/purge", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["colaboradores_purgados"] == 0
    assert data["colaboradores_anonimizados"] == 0


def test_anonimizacao(client, admin_headers):
    r = client.get("/api/colaboradores", headers=admin_headers)
    colab = r.json()[0]
    colab_id = colab["id"]

    r = client.delete(f"/api/colaboradores/{colab_id}", headers=admin_headers)
    assert r.status_code == 204

    r = client.delete(f"/api/colaboradores/{colab_id}/dados-pessoais", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert "anonimizados" in data["detail"]


def test_purge_after_anonymization(client, admin_headers):
    r = client.get("/api/colaboradores", headers=admin_headers)
    colab = r.json()[0]

    r = client.delete(f"/api/colaboradores/{colab['id']}", headers=admin_headers)
    r = client.delete(f"/api/colaboradores/{colab['id']}/dados-pessoais", headers=admin_headers)

    r = client.post("/api/purge", headers=admin_headers)
    assert r.status_code == 200


def test_config_retencao(client, admin_headers):
    r = client.get("/api/config", headers=admin_headers)
    assert r.status_code == 200
    assert r.json().get("retencao_dias") == "1825"


def test_superadmin_needs_tenant_for_create(client, admin_headers):
    r = client.post("/api/colaboradores", json={
        "nome": "Sem Tenant",
        "matricula": "ST001",
        "setor": "Teste",
        "funcao": "Teste",
        "consentimento_dados": True,
    }, headers=admin_headers)
    assert r.status_code == 400
    assert "selecionar um estado" in r.json()["detail"]
