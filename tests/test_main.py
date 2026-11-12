from tests.helpers import criar_candidato, criar_contratante, login


def test_pagina_inicial_retorna_200(client):
    response = client.get("/")
    assert response.status_code == 200


def test_pagina_inicial_contem_trampomatch(client):
    response = client.get("/")
    assert b"TrampoMatch" in response.data


def test_rota_index_alias_retorna_200(client):
    response = client.get("/index")
    assert response.status_code == 200


def test_pagina_inicial_apresenta_funcionalidades_principais(client):
    response = client.get("/")

    assert "Compatibilidade".encode() in response.data
    assert "Nível da vaga".encode() in response.data
    assert "Funcionalidades principais".encode() in response.data


def test_candidato_logado_nao_acessa_landing(client):
    criar_candidato(email="landing-candidato@test.com")
    login(client, "landing-candidato@test.com")

    response = client.get("/")

    assert response.status_code == 302
    assert "/candidato/dashboard" in response.headers["Location"]


def test_contratante_logado_nao_acessa_landing(client):
    criar_contratante(email="landing-contratante@test.com")
    login(client, "landing-contratante@test.com")

    response = client.get("/index")

    assert response.status_code == 302
    assert "/contratante/dashboard" in response.headers["Location"]
