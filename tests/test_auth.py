from io import BytesIO
from pathlib import Path

from trampomatch.models import Usuario
from trampomatch.models import PerfilCandidato, PerfilContratante

from tests.helpers import criar_candidato, criar_contratante, login


def test_pagina_login_retorna_200(client):
    response = client.get("/auth/login")
    assert response.status_code == 200


def test_cadastro_valido_redireciona(client):
    response = client.post(
        "/auth/cadastro",
        data={
            "nome": "João Silva",
            "email": "joao@teste.com",
            "senha": "senha123",
            "confirmar_senha": "senha123",
            "tipo_perfil": "candidato",
        },
    )

    assert response.status_code == 302
    assert Usuario.query.filter_by(email="joao@teste.com").first() is not None


def test_cadastro_email_duplicado_retorna_200(client):
    criar_candidato(email="duplicado@test.com")

    response = client.post(
        "/auth/cadastro",
        data={
            "nome": "Outro Usuário",
            "email": "duplicado@test.com",
            "senha": "senha123",
            "confirmar_senha": "senha123",
            "tipo_perfil": "candidato",
        },
    )

    assert response.status_code == 200
    assert "Este e-mail já está cadastrado".encode() in response.data


def test_login_valido_redireciona(client):
    criar_candidato(email="login@test.com")
    response = login(client, "login@test.com")
    assert response.status_code == 302
    assert "/candidato/dashboard" in response.headers["Location"]


def test_login_invalido_retorna_200(client):
    response = client.post(
        "/auth/login",
        data={"email": "naoexiste@test.com", "senha": "errada"},
    )
    assert response.status_code == 200
    assert "E-mail ou senha inválidos".encode() in response.data


def test_logout_redireciona_para_home(client):
    criar_candidato(email="logout@test.com")
    login(client, "logout@test.com")
    response = client.get("/auth/logout")
    assert response.status_code == 302


def definir_google_pending(client, **kwargs):
    dados = {
        "google_id": "google-123",
        "email": "google@test.com",
        "nome": "Google Teste",
    }
    dados.update(kwargs)
    with client.session_transaction() as session:
        session["google_pending"] = dados


def test_google_escolher_perfil_rejeita_tipo_invalido(client):
    definir_google_pending(client)

    response = client.post(
        "/auth/google/escolher-perfil",
        data={"tipo_perfil": "admin"},
    )

    assert response.status_code == 200
    assert "Escolha um tipo de perfil válido".encode() in response.data


def test_google_novo_candidato_completa_onboarding(client):
    definir_google_pending(client)

    response_escolha = client.post(
        "/auth/google/escolher-perfil",
        data={"tipo_perfil": "candidato"},
    )
    assert response_escolha.status_code == 302
    assert "/auth/google/completar-perfil" in response_escolha.headers["Location"]

    response = client.post(
        "/auth/google/completar-perfil",
        data={
            "regiao": "Vitória",
            "tipo_trabalho": "diaria",
            "disponibilidade": "manhã",
            "habilidades": "Limpeza, Organização",
            "experiencia_resumida": "Experiência em serviços gerais.",
            "nivel_experiencia": "30",
        },
    )

    usuario = Usuario.query.filter_by(email="google@test.com").first()
    perfil = PerfilCandidato.query.filter_by(usuario_id=usuario.id).first()

    assert response.status_code == 302
    assert "/candidato/dashboard" in response.headers["Location"]
    assert usuario.google_id == "google-123"
    assert usuario.tipo_perfil == "candidato"
    assert perfil.regiao == "Vitória"
    assert perfil.tipo_trabalho == "diaria"


def test_google_novo_contratante_completa_onboarding_com_logo(client, app):
    definir_google_pending(
        client,
        google_id="google-contratante",
        email="google-contratante@test.com",
        nome="Gabriel Oliveira",
    )

    response_escolha = client.post(
        "/auth/google/escolher-perfil",
        data={"tipo_perfil": "contratante"},
    )
    assert response_escolha.status_code == 302

    response = client.post(
        "/auth/google/completar-perfil",
        data={
            "logo_empresa": (BytesIO(b"fake-image"), "logo.png"),
            "nome_empresa": "Construções XYZ Ltda.",
            "regiao": "Vila Velha",
            "descricao": "Empresa especializada em reformas residenciais.",
            "tipo_contratante": "empresa",
            "quantidade_funcionarios": "1-10",
            "areas_atuacao": "Construção Civil, Reformas, Engenharia",
            "site": "https://xyz.example.com",
        },
        content_type="multipart/form-data",
    )

    usuario = Usuario.query.filter_by(email="google-contratante@test.com").first()
    perfil = PerfilContratante.query.filter_by(usuario_id=usuario.id).first()

    assert response.status_code == 302
    assert "/contratante/dashboard" in response.headers["Location"]
    assert usuario.google_id == "google-contratante"
    assert perfil.nome_empresa == "Construções XYZ Ltda."
    assert perfil.tipo_contratante == "empresa"
    assert perfil.quantidade_funcionarios == "1-10"
    assert perfil.areas_atuacao == "Construção Civil, Reformas, Engenharia"
    assert perfil.logo_empresa.startswith("uploads/logos_empresas/")
    assert (Path(app.instance_path) / perfil.logo_empresa).exists()


def test_google_onboarding_rejeita_formulario_incompleto(client):
    definir_google_pending(
        client,
        google_id="google-incompleto",
        email="google-incompleto@test.com",
        tipo_perfil="contratante",
    )

    response = client.post(
        "/auth/google/completar-perfil",
        data={"nome_empresa": ""},
    )

    assert response.status_code == 200
    assert Usuario.query.filter_by(email="google-incompleto@test.com").first() is None


def test_google_onboarding_rejeita_logo_extensao_invalida(client):
    definir_google_pending(
        client,
        google_id="google-logo-invalida",
        email="google-logo-invalida@test.com",
        tipo_perfil="contratante",
    )

    response = client.post(
        "/auth/google/completar-perfil",
        data={
            "logo_empresa": (BytesIO(b"fake-file"), "logo.gif"),
            "nome_empresa": "Empresa Teste",
            "regiao": "Vitória",
            "descricao": "Descrição válida da empresa.",
            "tipo_contratante": "empresa",
            "quantidade_funcionarios": "1-10",
            "areas_atuacao": "Limpeza",
            "site": "",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert "Envie uma imagem PNG ou JPG".encode() in response.data
    assert Usuario.query.filter_by(email="google-logo-invalida@test.com").first() is None


def test_google_onboarding_rejeita_logo_maior_que_2mb(client):
    definir_google_pending(
        client,
        google_id="google-logo-grande",
        email="google-logo-grande@test.com",
        tipo_perfil="contratante",
    )

    response = client.post(
        "/auth/google/completar-perfil",
        data={
            "logo_empresa": (BytesIO(b"x" * (2 * 1024 * 1024 + 1)), "logo.jpg"),
            "nome_empresa": "Empresa Teste",
            "regiao": "Vitória",
            "descricao": "Descrição válida da empresa.",
            "tipo_contratante": "empresa",
            "quantidade_funcionarios": "1-10",
            "areas_atuacao": "Limpeza",
            "site": "",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert "A logo deve ter no máximo 2 MB".encode() in response.data
    assert Usuario.query.filter_by(email="google-logo-grande@test.com").first() is None


def test_google_usuario_existente_com_google_id_entra_direto(client):
    usuario = criar_contratante(email="google-existente@test.com")
    usuario.google_id = "google-existente"
    from trampomatch.extensions import db

    db.session.commit()

    definir_google_pending(
        client,
        google_id="google-existente",
        email="google-existente@test.com",
    )

    response = client.get("/auth/google/escolher-perfil")

    assert response.status_code == 302
    assert "/contratante/dashboard" in response.headers["Location"]
