import io
from pathlib import Path

from tests.helpers import criar_candidato, criar_contratante, login
from sqlalchemy import inspect, text
from trampomatch import ensure_sqlite_schema
from trampomatch.models import PerfilCandidato, PerfilContratante


def test_rota_protegida_redireciona_anonimo(client):
    response = client.get("/candidato/dashboard")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_candidato_nao_acessa_area_contratante(client):
    criar_candidato(email="cand403@test.com")
    login(client, "cand403@test.com")
    response = client.get("/contratante/dashboard")
    assert response.status_code == 403


def test_contratante_nao_acessa_area_candidato(client):
    criar_contratante(email="cont403@test.com")
    login(client, "cont403@test.com")
    response = client.get("/candidato/dashboard")
    assert response.status_code == 403


def test_cria_perfil_candidato(client):
    criar_candidato(email="semperfil@test.com", com_perfil=False)
    login(client, "semperfil@test.com")
    response = client.post(
        "/candidato/perfil",
        data={
            "regiao": "Vitória",
            "categoria": "servicos_gerais",
            "tipo_trabalho": "diaria",
            "disponibilidade": "manhã",
            "habilidades": "limpeza, organização",
            "experiencia_resumida": "Experiência local",
            "nivel_experiencia": 55,
        },
    )
    assert response.status_code == 302


def test_perfil_candidato_aceita_habilidade_customizada(client):
    usuario = criar_candidato(email="habilidadecustom@test.com", com_perfil=False)
    login(client, usuario.email)

    response = client.post(
        "/candidato/perfil",
        data={
            "regiao": "Cariacica",
            "categoria": "servicos_gerais",
            "tipo_trabalho": "temporario",
            "disponibilidade": "flexível",
            "habilidades": "solda artesanal, atendimento ao cliente",
            "experiencia_resumida": "Trabalhos variados",
            "nivel_experiencia": 80,
        },
    )

    perfil = PerfilCandidato.query.filter_by(usuario_id=usuario.id).first()
    assert response.status_code == 302
    assert "solda artesanal" in perfil.habilidades
    assert perfil.nivel_experiencia == 80


def test_perfil_candidato_renderiza_modal_curriculo(client):
    usuario = criar_candidato(email="curriculo-ui@test.com")
    login(client, usuario.email)

    response = client.get("/candidato/perfil")

    assert response.status_code == 200
    assert "Enviar currículo".encode() in response.data
    assert b"modal-curriculo" in response.data
    assert b"modal-curriculo-visualizar" in response.data


def test_candidato_envia_baixa_substitui_e_remove_curriculo(client, app):
    usuario = criar_candidato(email="curriculo@test.com")
    login(client, usuario.email)

    response = client.post(
        "/candidato/perfil/curriculo",
        data={"curriculo": (io.BytesIO(b"%PDF-1.4 teste"), "curriculo.pdf")},
    )

    perfil = PerfilCandidato.query.filter_by(usuario_id=usuario.id).first()
    primeiro_arquivo = perfil.curriculo_arquivo
    primeiro_caminho = (
        Path(app.instance_path) / "uploads" / "curriculos" / primeiro_arquivo
    )
    assert response.status_code == 302
    assert perfil.curriculo_nome_original == "curriculo.pdf"
    assert primeiro_caminho.exists()

    download = client.get("/candidato/perfil/curriculo")
    assert download.status_code == 200
    assert b"%PDF-1.4 teste" in download.data
    download.close()

    preview = client.get("/candidato/perfil/curriculo/visualizar")
    assert preview.status_code == 200
    assert b"%PDF-1.4 teste" in preview.data
    preview.close()

    client.post(
        "/candidato/perfil/curriculo",
        data={"curriculo": (io.BytesIO(b"%PDF-1.4 novo"), "novo.pdf")},
    )
    assert not primeiro_caminho.exists()
    assert perfil.curriculo_nome_original == "novo.pdf"
    assert perfil.curriculo_arquivo != primeiro_arquivo

    response = client.post("/candidato/perfil/curriculo/remover")
    assert response.status_code == 302
    assert perfil.curriculo_arquivo is None
    assert perfil.curriculo_nome_original is None


def test_curriculo_rejeita_extensao_invalida(client):
    usuario = criar_candidato(email="curriculo-ext@test.com")
    login(client, usuario.email)

    response = client.post(
        "/candidato/perfil/curriculo",
        data={"curriculo": (io.BytesIO(b"arquivo"), "curriculo.exe")},
    )

    perfil = PerfilCandidato.query.filter_by(usuario_id=usuario.id).first()
    assert response.status_code == 302
    assert perfil.curriculo_arquivo is None


def test_curriculo_rejeita_arquivo_maior_que_5mb(client):
    usuario = criar_candidato(email="curriculo-grande@test.com")
    login(client, usuario.email)

    response = client.post(
        "/candidato/perfil/curriculo",
        data={
            "curriculo": (
                io.BytesIO(b"x" * (5 * 1024 * 1024 + 1)),
                "grande.pdf",
            )
        },
    )

    perfil = PerfilCandidato.query.filter_by(usuario_id=usuario.id).first()
    assert response.status_code == 302
    assert perfil.curriculo_arquivo is None


def test_acesso_curriculo_exige_perfil_correto(client):
    candidato = criar_candidato(email="curriculo-acesso-cand@test.com")
    contratante = criar_contratante(email="curriculo-acesso-cont@test.com")

    response = client.get("/candidato/perfil/curriculo")
    assert response.status_code == 302

    login(client, candidato.email)
    response = client.get(f"/contratante/candidatos/{candidato.id}/curriculo")
    assert response.status_code == 403

    client.get("/auth/logout")
    login(client, contratante.email)
    response = client.get("/candidato/perfil/curriculo")
    assert response.status_code == 403


def test_contratante_baixa_curriculo_do_candidato(client):
    candidato = criar_candidato(email="curriculo-cont-cand@test.com")
    contratante = criar_contratante(email="curriculo-cont@test.com")
    login(client, candidato.email)
    client.post(
        "/candidato/perfil/curriculo",
        data={"curriculo": (io.BytesIO(b"doc"), "curriculo.doc")},
    )

    client.get("/auth/logout")
    login(client, contratante.email)
    response = client.get(f"/contratante/candidatos/{candidato.id}/curriculo")

    assert response.status_code == 200
    assert response.data == b"doc"
    response.close()
    preview = client.get(
        f"/contratante/candidatos/{candidato.id}/curriculo/visualizar"
    )
    assert preview.status_code == 200
    assert preview.data == b"doc"
    preview.close()
    caminho = (
        Path("instance")
        / "uploads"
        / "curriculos"
        / candidato.perfil_candidato.curriculo_arquivo
    )
    if caminho.exists():
        caminho.unlink()


def test_cria_perfil_contratante(client):
    usuario = criar_contratante(email="contperfil@test.com", com_perfil=False)
    login(client, "contperfil@test.com")
    response = client.post(
        "/contratante/perfil",
        data={
            "nome_empresa": "Empresa Local",
            "regiao": "Vitória",
            "descricao": "Empresa local",
            "tipo_contratante": "empresa",
            "quantidade_funcionarios": "1-10",
            "areas_atuacao": "Comércio, Serviços",
            "site": "",
        },
    )
    perfil = PerfilContratante.query.filter_by(usuario_id=usuario.id).first()

    assert response.status_code == 302
    assert perfil.nome_empresa == "Empresa Local"
    assert perfil.regiao == "Vitória"
    assert perfil.tipo_contratante == "empresa"
    assert perfil.areas_atuacao == "Comércio, Serviços"


def test_perfil_contratante_renderiza_tela_completa(client):
    usuario = criar_contratante(email="contperfil-ui@test.com", com_perfil=False)
    login(client, usuario.email)

    response = client.get("/contratante/perfil")

    assert response.status_code == 200
    assert "Dados da empresa".encode() in response.data
    assert "Detalhes do contratante".encode() in response.data
    assert "Confirmação".encode() in response.data
    assert "Concluir perfil".encode() in response.data
    assert "Logo da empresa".encode() in response.data
    assert "Área de atuação".encode() in response.data
    assert "Como candidatos verão sua empresa".encode() in response.data
    assert b"preview-company-name" in response.data
    assert b"preview-company-areas" in response.data


def test_migracao_adiciona_areas_atuacao_em_banco_antigo(db):
    db.drop_all()
    db.session.execute(
        text(
            """
            CREATE TABLE perfis_contratantes (
                id INTEGER PRIMARY KEY,
                usuario_id INTEGER NOT NULL UNIQUE,
                regiao VARCHAR(100) NOT NULL,
                descricao TEXT
            )
            """
        )
    )
    db.session.commit()

    ensure_sqlite_schema()

    colunas = {c["name"] for c in inspect(db.engine).get_columns("perfis_contratantes")}
    assert "areas_atuacao" in colunas


def test_migracao_adiciona_curriculo_em_banco_antigo(db):
    db.drop_all()
    db.session.execute(
        text(
            """
            CREATE TABLE perfis_candidatos (
                id INTEGER PRIMARY KEY,
                usuario_id INTEGER NOT NULL UNIQUE,
                regiao VARCHAR(100) NOT NULL,
                tipo_trabalho VARCHAR(50) NOT NULL,
                disponibilidade VARCHAR(100) NOT NULL,
                habilidades TEXT NOT NULL,
                experiencia_resumida TEXT,
                nivel_experiencia INTEGER NOT NULL
            )
            """
        )
    )
    db.session.commit()

    ensure_sqlite_schema()

    colunas = {c["name"] for c in inspect(db.engine).get_columns("perfis_candidatos")}
    assert "curriculo_arquivo" in colunas
    assert "curriculo_nome_original" in colunas
    assert "curriculo_enviado_em" in colunas


def test_contratante_sem_perfil_nao_acessa_nova_vaga(client):
    usuario = criar_contratante(email="semperfil-vaga@test.com", com_perfil=False)
    login(client, usuario.email)

    response = client.get("/contratante/vagas/nova")

    assert response.status_code == 302
    assert "/contratante/perfil" in response.headers["Location"]
