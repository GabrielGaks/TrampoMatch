from trampomatch.extensions import db
from trampomatch.models import (
    DescarteContratante,
    DescarteVaga,
    Interesse,
    InteresseContratante,
    Match,
    RecusaCandidaturaVaga,
    Vaga,
)

from tests.helpers import criar_candidato, criar_contratante, criar_vaga, login


def test_contratante_cadastra_edita_e_encerra_vaga(client):
    criar_contratante(email="dono@test.com")
    login(client, "dono@test.com")

    response = client.post(
        "/contratante/vagas/nova",
        data={
            "titulo": "Entregador",
            "descricao": "Entregas locais",
            "regiao": "Vitória",
            "categoria": "transporte",
            "tipo_vaga": "diaria",
            "valor_min": 100,
            "valor_max": 150,
            "habilidades_desejadas": "direção, agilidade",
            "complexidade": 70,
            "status": "aberta",
        },
    )
    assert response.status_code == 302
    vaga = Vaga.query.filter_by(titulo="Entregador").first()
    assert vaga is not None

    response = client.post(
        f"/contratante/vagas/{vaga.id}/editar",
        data={
            "titulo": "Entregador Local",
            "descricao": "Entregas locais",
            "regiao": "Vitória",
            "categoria": "transporte",
            "tipo_vaga": "diaria",
            "valor_min": 100,
            "valor_max": 150,
            "habilidades_desejadas": "direção, agilidade",
            "complexidade": 70,
            "status": "aberta",
        },
    )
    assert response.status_code == 302
    assert db.session.get(Vaga, vaga.id).titulo == "Entregador Local"

    response = client.post(f"/contratante/vagas/{vaga.id}/encerrar")
    assert response.status_code == 302
    assert db.session.get(Vaga, vaga.id).status == "encerrada"


def test_bloqueia_edicao_de_vaga_de_outro_contratante(client):
    dono = criar_contratante(email="dono2@test.com")
    outro = criar_contratante(email="outro@test.com")
    vaga = criar_vaga(dono)
    login(client, outro.email)
    response = client.get(f"/contratante/vagas/{vaga.id}/editar")
    assert response.status_code == 403


def test_listagem_de_vagas_abertas_com_filtro(client):
    contratante = criar_contratante(email="lista-cont@test.com")
    criar_vaga(contratante, titulo="Vaga Vitória", regiao="Vitória")
    criar_vaga(contratante, titulo="Vaga Serra", regiao="Serra")
    criar_candidato(email="lista-cand@test.com")
    login(client, "lista-cand@test.com")

    response = client.get("/vagas/?regiao=Vitória")
    assert response.status_code == 200
    assert "Descobrir vagas".encode() in response.data
    assert "Vaga Vitória".encode() in response.data
    assert "Vaga Serra".encode() not in response.data


def test_listagem_sem_filtro_exibe_vagas_de_outras_regioes(client):
    contratante = criar_contratante(email="regiao-cont@test.com")
    criar_vaga(contratante, titulo="Vaga Vila Velha", regiao="Vila Velha")
    criar_vaga(contratante, titulo="Vaga Vitória distante", regiao="Vitória")
    candidato = criar_candidato(email="regiao-cand@test.com")
    candidato.perfil_candidato.regiao = "Vila Velha"
    db.session.commit()
    login(client, candidato.email)

    response = client.get("/vagas/")

    assert response.status_code == 200
    assert "Vaga Vila Velha".encode() in response.data
    assert "Vaga Vitória distante".encode() in response.data


def test_descoberta_candidatos_mostra_link_de_curriculo(client):
    contratante = criar_contratante(email="desc-cv-cont@test.com")
    candidato = criar_candidato(email="desc-cv-cand@test.com")
    candidato.perfil_candidato.curriculo_arquivo = "curriculo.pdf"
    candidato.perfil_candidato.curriculo_nome_original = "curriculo.pdf"
    db.session.commit()
    login(client, contratante.email)

    response = client.get("/contratante/candidatos")

    assert response.status_code == 200
    assert f"/contratante/candidatos/{candidato.id}/curriculo".encode() in response.data
    assert f"/contratante/candidatos/{candidato.id}/curriculo/visualizar".encode() in response.data
    assert "Ver currículo".encode() in response.data


def test_descoberta_candidatos_filtra_por_categoria_da_vaga_selecionada(client):
    contratante = criar_contratante(email="cat-vaga-cont@test.com")
    vaga = criar_vaga(contratante, titulo="Dev Python", categoria="tecnologia")
    criar_candidato(
        email="tech@test.com",
        nome="Candidato Tech",
        categoria="tecnologia",
    )
    criar_candidato(
        email="admin@test.com",
        nome="Candidato Admin",
        categoria="administrativo",
    )
    login(client, contratante.email)

    response = client.get(f"/contratante/candidatos?vaga_id={vaga.id}")

    assert response.status_code == 200
    assert "Candidato Tech".encode() in response.data
    assert "Candidato Admin".encode() not in response.data
    assert "Mostrando candidatos da categoria:".encode() in response.data
    assert "Tecnologia / TI".encode() in response.data


def test_descoberta_candidatos_filtra_uniao_categorias_sem_vaga_selecionada(client):
    contratante = criar_contratante(email="cat-uniao-cont@test.com")
    criar_vaga(contratante, titulo="Dev", categoria="tecnologia")
    criar_vaga(contratante, titulo="Vendedor", categoria="comercio_vendas")
    criar_candidato(
        email="tech-uniao@test.com",
        nome="Tech Uniao",
        categoria="tecnologia",
    )
    criar_candidato(
        email="vendas-uniao@test.com",
        nome="Vendas Uniao",
        categoria="comercio_vendas",
    )
    criar_candidato(
        email="obra-uniao@test.com",
        nome="Obra Uniao",
        categoria="construcao",
    )
    login(client, contratante.email)

    response = client.get("/contratante/candidatos")

    assert response.status_code == 200
    assert "Tech Uniao".encode() in response.data
    assert "Vendas Uniao".encode() in response.data
    assert "Obra Uniao".encode() not in response.data
    assert "Mostrando candidatos das categorias das suas vagas abertas.".encode() in response.data


def test_descoberta_candidatos_sem_categoria_nas_vagas_nao_filtra(client):
    contratante = criar_contratante(email="cat-legado-cont@test.com")
    criar_vaga(contratante, titulo="Vaga legada")
    criar_candidato(
        email="sem-cat@test.com",
        nome="Sem Categoria",
        categoria=None,
    )
    login(client, contratante.email)

    response = client.get("/contratante/candidatos")

    assert response.status_code == 200
    assert "Sem Categoria".encode() in response.data
    assert "Mostrando candidatos da categoria:".encode() not in response.data
    assert (
        "Mostrando candidatos das categorias das suas vagas abertas.".encode()
        not in response.data
    )


def test_listagem_exibe_nivel_da_vaga_sem_filtros_antigos(client):
    contratante = criar_contratante(email="nivel-cont@test.com")
    criar_vaga(contratante, titulo="Vaga com nivel", complexidade=70)
    criar_candidato(email="nivel-cand@test.com")
    login(client, "nivel-cand@test.com")

    response = client.get("/vagas/")

    assert response.status_code == 200
    assert b"data-swipe-feedback" in response.data
    assert "Nível da vaga".encode() in response.data
    assert "Complexidade mínima".encode() not in response.data
    assert "Complexidade máxima".encode() not in response.data


def test_listagem_aceita_ordenacao_por_recentes_e_filtro_de_nivel(client):
    contratante = criar_contratante(email="ordenar-cont@test.com")
    criar_vaga(contratante, titulo="Vaga alta", complexidade=70)
    criar_candidato(email="ordenar-cand@test.com")
    login(client, "ordenar-cand@test.com")

    response = client.get("/vagas/?ordenar=recentes&complexidade=alta")

    assert response.status_code == 200
    assert "Vaga alta".encode() in response.data


def test_descartar_vaga_remove_do_deck(client):
    contratante = criar_contratante(email="descarte-cont@test.com")
    vaga = criar_vaga(contratante, titulo="Vaga para descartar")
    candidato = criar_candidato(email="descarte-cand@test.com")
    login(client, candidato.email)

    response = client.post(f"/vagas/{vaga.id}/descartar")

    assert response.status_code == 302
    assert (
        DescarteVaga.query.filter_by(candidato_id=candidato.id, vaga_id=vaga.id).count()
        == 1
    )

    response = client.get("/vagas/")
    assert "Vaga para descartar".encode() not in response.data


def test_interesse_via_deck_remove_vaga_do_deck(client):
    contratante = criar_contratante(email="deck-cont@test.com")
    vaga = criar_vaga(contratante, titulo="Vaga curtida no deck")
    candidato = criar_candidato(email="deck-cand@test.com")
    login(client, candidato.email)

    response = client.post(f"/vagas/{vaga.id}/interesse")

    assert response.status_code == 302
    assert (
        Interesse.query.filter_by(candidato_id=candidato.id, vaga_id=vaga.id).count()
        == 1
    )

    response = client.get("/vagas/")
    assert "Vaga curtida no deck".encode() not in response.data


def test_candidato_visualiza_minhas_vagas_aceitas(client):
    contratante = criar_contratante(email="minhas-cont@test.com")
    vaga = criar_vaga(contratante, titulo="Vaga aceita pelo candidato")
    candidato = criar_candidato(email="minhas-cand@test.com")
    login(client, candidato.email)
    client.post(f"/vagas/{vaga.id}/interesse")

    response = client.get("/candidato/minhas-vagas")

    assert response.status_code == 200
    assert "Minhas vagas".encode() in response.data
    assert "Vaga aceita pelo candidato".encode() in response.data
    assert b"tm-minhas-vagas-candidato" in response.data
    assert "Nível da vaga".encode() in response.data
    assert "Complexidade".encode() not in response.data


def test_contratante_minhas_vagas_renderiza_tabela_responsiva(client):
    contratante = criar_contratante(email="minhas-mobile-cont@test.com")
    criar_vaga(contratante, titulo="Vaga responsiva")
    login(client, contratante.email)

    response = client.get("/contratante/vagas")

    assert response.status_code == 200
    assert b"tm-minhas-vagas-contratante" in response.data
    assert b'data-label="T\xc3\xadtulo"' in response.data
    assert b'data-label="Regi\xc3\xa3o"' in response.data
    assert b'data-label="Status"' in response.data
    assert b'data-label="N\xc3\xadvel da vaga"' in response.data
    assert b'data-label="A\xc3\xa7\xc3\xb5es"' in response.data
    assert "Nível da vaga".encode() in response.data
    assert "Complexidade".encode() not in response.data


def test_acoes_do_deck_respondem_json_sem_redirecionar(client):
    contratante = criar_contratante(email="ajax-cont@test.com")
    vaga_like = criar_vaga(contratante, titulo="Vaga Ajax Like")
    vaga_skip = criar_vaga(contratante, titulo="Vaga Ajax Skip")
    candidato = criar_candidato(email="ajax-cand@test.com")
    login(client, candidato.email)

    headers = {"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"}
    response_like = client.post(f"/vagas/{vaga_like.id}/interesse", headers=headers)
    response_skip = client.post(f"/vagas/{vaga_skip.id}/descartar", headers=headers)

    assert response_like.status_code == 200
    assert response_like.get_json()["action"] == "like"
    assert response_skip.status_code == 200
    assert response_skip.get_json()["action"] == "skip"


def test_interesse_unico_remocao_e_interessados(client):
    contratante = criar_contratante(email="interesse-cont@test.com")
    vaga = criar_vaga(contratante)
    candidato = criar_candidato(email="interesse-cand@test.com")
    candidato.perfil_candidato.curriculo_arquivo = "curriculo.pdf"
    candidato.perfil_candidato.curriculo_nome_original = "curriculo.pdf"
    db.session.commit()
    login(client, candidato.email)

    response = client.post(f"/vagas/{vaga.id}/interesse")
    assert response.status_code == 302
    assert (
        Interesse.query.filter_by(candidato_id=candidato.id, vaga_id=vaga.id).count()
        == 1
    )

    client.post(f"/vagas/{vaga.id}/interesse")
    assert (
        Interesse.query.filter_by(candidato_id=candidato.id, vaga_id=vaga.id).count()
        == 1
    )

    response = client.post(f"/vagas/{vaga.id}/remover_interesse")
    assert response.status_code == 302
    assert (
        Interesse.query.filter_by(candidato_id=candidato.id, vaga_id=vaga.id).count()
        == 0
    )

    client.post(f"/vagas/{vaga.id}/interesse")
    client.get("/auth/logout")
    login(client, contratante.email)
    response = client.get(f"/contratante/vagas/{vaga.id}/interessados")
    assert response.status_code == 200
    assert candidato.nome.encode() in response.data
    assert f"/contratante/candidatos/{candidato.id}/curriculo".encode() in response.data
    assert f"/contratante/candidatos/{candidato.id}/curriculo/visualizar".encode() in response.data


def test_empresa_curte_candidato_e_candidato_ve_convite(client):
    contratante = criar_contratante(email="convite-cont@test.com")
    vaga = criar_vaga(contratante, titulo="Convite para candidato")
    candidato = criar_candidato(email="convite-cand@test.com")
    login(client, contratante.email)

    response = client.post(
        f"/contratante/candidatos/{candidato.id}/interesse",
        data={"vaga_id": vaga.id},
    )
    assert response.status_code == 302
    assert (
        InteresseContratante.query.filter_by(
            contratante_id=contratante.id,
            candidato_id=candidato.id,
            vaga_id=vaga.id,
        ).count()
        == 1
    )

    client.get("/auth/logout")
    login(client, candidato.email)
    response = client.get("/candidato/convites")

    assert response.status_code == 200
    assert "Convite para candidato".encode() in response.data
    assert "Convites".encode() in response.data


def test_contratante_abre_detalhes_do_candidato_curtido(client):
    contratante = criar_contratante(email="curtidos-cont@test.com")
    vaga = criar_vaga(contratante, titulo="Vaga do candidato curtido")
    candidato = criar_candidato(email="curtidos-cand@test.com")
    candidato.perfil_candidato.curriculo_arquivo = "curriculo.pdf"
    candidato.perfil_candidato.curriculo_nome_original = "curriculo.pdf"
    db.session.add(
        InteresseContratante(
            contratante_id=contratante.id,
            candidato_id=candidato.id,
            vaga_id=vaga.id,
        )
    )
    db.session.commit()
    login(client, contratante.email)

    response = client.get("/contratante/candidatos/respondidos")

    assert response.status_code == 200
    alvo_modal = f'data-target="modal-{candidato.id}-{vaga.id}"'
    assert alvo_modal.encode() in response.data
    assert candidato.email.encode() in response.data
    assert "Experiência em serviços gerais.".encode() in response.data
    assert b"Disponibilidade" in response.data
    assert f"/contratante/candidatos/{candidato.id}/curriculo".encode() in response.data
    assert f"/contratante/candidatos/{candidato.id}/curriculo/visualizar".encode() in response.data
    assert b"curriculo.pdf" in response.data


def test_candidato_aceita_convite_e_cria_match_com_vaga(client):
    contratante = criar_contratante(email="aceita-cont@test.com")
    vaga = criar_vaga(contratante, titulo="Vaga aceita por convite")
    candidato = criar_candidato(email="aceita-cand@test.com")
    convite = InteresseContratante(
        contratante_id=contratante.id,
        candidato_id=candidato.id,
        vaga_id=vaga.id,
    )
    db.session.add(convite)
    db.session.commit()
    login(client, candidato.email)

    response = client.post(f"/candidato/convites/{convite.id}/aceitar")

    assert response.status_code == 302
    assert (
        Interesse.query.filter_by(candidato_id=candidato.id, vaga_id=vaga.id).count()
        == 1
    )
    match = Match.query.filter_by(
        candidato_id=candidato.id,
        contratante_id=contratante.id,
        vaga_id=vaga.id,
        status="ativo",
    ).first()
    assert match is not None


def test_candidato_recusa_convite_e_convite_some(client):
    contratante = criar_contratante(email="recusa-cont@test.com")
    vaga = criar_vaga(contratante, titulo="Vaga recusada por convite")
    candidato = criar_candidato(email="recusa-cand@test.com")
    convite = InteresseContratante(
        contratante_id=contratante.id,
        candidato_id=candidato.id,
        vaga_id=vaga.id,
    )
    db.session.add(convite)
    db.session.commit()
    login(client, candidato.email)

    response = client.post(f"/candidato/convites/{convite.id}/recusar")

    assert response.status_code == 302
    assert (
        DescarteVaga.query.filter_by(candidato_id=candidato.id, vaga_id=vaga.id).count()
        == 1
    )
    response = client.get("/candidato/convites")
    assert "Vaga recusada por convite".encode() not in response.data


def test_empresa_aceita_interessado_e_cria_match_com_vaga(client):
    contratante = criar_contratante(email="swipe-cont@test.com")
    vaga = criar_vaga(contratante, titulo="Vaga com interessado")
    candidato = criar_candidato(email="swipe-cand@test.com")
    db.session.add(Interesse(candidato_id=candidato.id, vaga_id=vaga.id))
    db.session.commit()
    login(client, contratante.email)

    response = client.get(f"/contratante/vagas/{vaga.id}/interessados")
    assert response.status_code == 200
    assert candidato.nome.encode() in response.data

    response = client.post(
        f"/contratante/vagas/{vaga.id}/interessados/{candidato.id}/aceitar"
    )

    assert response.status_code == 302
    assert (
        InteresseContratante.query.filter_by(
            contratante_id=contratante.id,
            candidato_id=candidato.id,
            vaga_id=vaga.id,
        ).count()
        == 1
    )
    assert (
        Match.query.filter_by(
            candidato_id=candidato.id,
            contratante_id=contratante.id,
            vaga_id=vaga.id,
            status="ativo",
        ).count()
        == 1
    )


def test_dashboard_vagas_abertas_respeita_categoria_e_recusas(client):
    contratante = criar_contratante(email="dash-vagas-cont@test.com")
    criar_vaga(contratante, titulo="Vaga Tech", categoria="tecnologia")
    criar_vaga(contratante, titulo="Vaga Admin", categoria="administrativo")
    criar_vaga(contratante, titulo="Vaga Tech Recusada", categoria="tecnologia")
    vaga_recusada = Vaga.query.filter_by(titulo="Vaga Tech Recusada").first()
    candidato = criar_candidato(
        email="dash-vagas-cand@test.com",
        categoria="tecnologia",
    )
    db.session.add(
        RecusaCandidaturaVaga(
            candidato_id=candidato.id,
            vaga_id=vaga_recusada.id,
            contratante_id=contratante.id,
        )
    )
    db.session.commit()
    login(client, candidato.email)

    response = client.get("/candidato/dashboard")
    assert response.status_code == 200
    assert "Vaga Admin".encode() not in response.data
    assert "Vaga Tech Recusada".encode() not in response.data
    assert b'tm-dash-stat-value--blue">1<' in response.data

    response_listagem = client.get("/vagas/")
    assert "Vaga Admin".encode() not in response_listagem.data
    assert "Vaga Tech Recusada".encode() not in response_listagem.data


def test_contador_interessados_exclui_aceitos_e_recusados(client):
    contratante = criar_contratante(email="contador-interesse-cont@test.com")
    vaga = criar_vaga(contratante, titulo="Vaga contador interessados")
    candidato = criar_candidato(email="contador-interesse-cand@test.com")
    db.session.add(Interesse(candidato_id=candidato.id, vaga_id=vaga.id))
    db.session.commit()

    login(client, contratante.email)
    response = client.get("/contratante/vagas")
    assert b"1 interessado" in response.data

    client.post(
        f"/contratante/vagas/{vaga.id}/interessados/{candidato.id}/aceitar"
    )
    response = client.get("/contratante/vagas")
    assert b"0 interessados" in response.data

    candidato2 = criar_candidato(email="contador-interesse-cand2@test.com")
    db.session.add(Interesse(candidato_id=candidato2.id, vaga_id=vaga.id))
    db.session.commit()
    response = client.get("/contratante/vagas")
    assert b"1 interessado" in response.data

    client.post(
        f"/contratante/vagas/{vaga.id}/interessados/{candidato2.id}/recusar"
    )
    response = client.get("/contratante/vagas")
    assert b"0 interessados" in response.data


def test_empresa_recusa_interessado_e_remove_da_fila(client):
    contratante = criar_contratante(email="recusa-interessado-cont@test.com")
    vaga = criar_vaga(contratante, titulo="Vaga com interessado recusado")
    candidato = criar_candidato(email="recusa-interessado-cand@test.com")
    db.session.add(Interesse(candidato_id=candidato.id, vaga_id=vaga.id))
    db.session.commit()
    login(client, contratante.email)

    response = client.post(
        f"/contratante/vagas/{vaga.id}/interessados/{candidato.id}/recusar"
    )

    assert response.status_code == 302
    assert (
        DescarteContratante.query.filter_by(
            contratante_id=contratante.id, candidato_id=candidato.id
        ).count()
        == 1
    )
    response = client.get(f"/contratante/vagas/{vaga.id}/interessados")
    assert candidato.nome.encode() not in response.data


def test_recusa_interessado_bloqueia_nova_candidatura_na_mesma_vaga(client):
    contratante = criar_contratante(email="bloqueio-recusa-cont@test.com")
    vaga = criar_vaga(contratante, titulo="Vaga bloqueada apos recusa")
    candidato = criar_candidato(email="bloqueio-recusa-cand@test.com")
    db.session.add(Interesse(candidato_id=candidato.id, vaga_id=vaga.id))
    db.session.commit()

    login(client, contratante.email)
    response_recusa = client.post(
        f"/contratante/vagas/{vaga.id}/interessados/{candidato.id}/recusar"
    )
    assert response_recusa.status_code == 302
    assert (
        RecusaCandidaturaVaga.query.filter_by(
            candidato_id=candidato.id, vaga_id=vaga.id
        ).count()
        == 1
    )
    assert (
        Interesse.query.filter_by(candidato_id=candidato.id, vaga_id=vaga.id).count()
        == 0
    )

    client.get("/auth/logout")
    login(client, candidato.email)
    response_interesse = client.post(f"/vagas/{vaga.id}/interesse")
    assert response_interesse.status_code == 302
    assert (
        Interesse.query.filter_by(candidato_id=candidato.id, vaga_id=vaga.id).count()
        == 0
    )

    response_listagem = client.get("/vagas/")
    assert vaga.titulo.encode() not in response_listagem.data

    response_detalhe = client.get(f"/vagas/{vaga.id}")
    assert response_detalhe.status_code == 200
    assert b"se candidatar novamente" in response_detalhe.data


def criar_match_teste(contratante_email, candidato_email, titulo_vaga="Vaga Match"):
    contratante = criar_contratante(email=contratante_email)
    candidato = criar_candidato(email=candidato_email)
    vaga = criar_vaga(contratante, titulo=titulo_vaga)
    match = Match(
        candidato_id=candidato.id,
        contratante_id=contratante.id,
        vaga_id=vaga.id,
        status="ativo",
    )
    db.session.add(match)
    db.session.commit()
    return contratante, candidato, vaga, match


def test_matches_contratante_mostra_link_de_curriculo(client):
    contratante, candidato, _, _ = criar_match_teste(
        "match-cv-cont@test.com", "match-cv-cand@test.com"
    )
    candidato.perfil_candidato.curriculo_arquivo = "curriculo.pdf"
    candidato.perfil_candidato.curriculo_nome_original = "curriculo.pdf"
    db.session.commit()
    login(client, contratante.email)

    response = client.get("/contratante/matches")

    assert response.status_code == 200
    assert f"/contratante/candidatos/{candidato.id}/curriculo".encode() in response.data
    assert "Ver currículo".encode() in response.data


def test_contratante_acessa_formulario_de_mensagem_do_match_proprio(client):
    contratante, _, vaga, match = criar_match_teste(
        "msg-form-cont@test.com", "msg-form-cand@test.com", "Auxiliar pós-match"
    )
    login(client, contratante.email)

    response = client.get(f"/contratante/matches/{match.id}/mensagem")

    assert response.status_code == 200
    assert "Mensagem pós-match".encode() in response.data
    assert vaga.titulo.encode() in response.data


def test_contratante_nao_acessa_mensagem_de_match_de_outro_contratante(client):
    _, _, _, match = criar_match_teste(
        "msg-outro-dono@test.com", "msg-outro-cand@test.com"
    )
    outro = criar_contratante(email="msg-invasor@test.com")
    login(client, outro.email)

    response = client.get(f"/contratante/matches/{match.id}/mensagem")

    assert response.status_code == 404


def test_mensagem_match_exige_texto_e_meio_de_contato(client):
    contratante, _, _, match = criar_match_teste(
        "msg-invalid-cont@test.com", "msg-invalid-cand@test.com"
    )
    login(client, contratante.email)

    response_sem_texto = client.post(
        f"/contratante/matches/{match.id}/mensagem",
        data={"usar_email": "y", "contato_email": "contato@empresa.com"},
    )
    response_sem_contato = client.post(
        f"/contratante/matches/{match.id}/mensagem",
        data={"mensagem": "Vamos conversar sobre a vaga."},
    )

    db.session.refresh(match)
    assert response_sem_texto.status_code == 200
    assert response_sem_contato.status_code == 200
    assert match.mensagem_contratante is None
    assert (
        "Selecione pelo menos um meio de contato.".encode() in response_sem_contato.data
    )


def test_mensagem_match_salva_email(client):
    contratante, _, _, match = criar_match_teste(
        "msg-email-cont@test.com", "msg-email-cand@test.com"
    )
    login(client, contratante.email)

    response = client.post(
        f"/contratante/matches/{match.id}/mensagem",
        data={
            "mensagem": "Envie seu currículo por e-mail.",
            "usar_email": "y",
            "contato_email": "rh@empresa.com",
        },
    )

    db.session.refresh(match)
    assert response.status_code == 302
    assert match.mensagem_contratante == "Envie seu currículo por e-mail."
    assert match.contato_email == "rh@empresa.com"
    assert match.contato_telefone is None
    assert match.mensagem_enviada_em is not None


def test_mensagem_match_salva_telefone(client):
    contratante, _, _, match = criar_match_teste(
        "msg-phone-cont@test.com", "msg-phone-cand@test.com"
    )
    login(client, contratante.email)

    response = client.post(
        f"/contratante/matches/{match.id}/mensagem",
        data={
            "mensagem": "Fale com nosso RH pelo telefone.",
            "usar_telefone": "y",
            "contato_telefone": "(27) 99999-1111",
        },
    )

    db.session.refresh(match)
    assert response.status_code == 302
    assert match.contato_email is None
    assert match.contato_telefone == "(27) 99999-1111"
    assert match.mensagem_enviada_em is not None


def test_mensagem_match_salva_email_e_telefone(client):
    contratante, _, _, match = criar_match_teste(
        "msg-both-cont@test.com", "msg-both-cand@test.com"
    )
    login(client, contratante.email)

    response = client.post(
        f"/contratante/matches/{match.id}/mensagem",
        data={
            "mensagem": "Escolha o melhor canal para falar conosco.",
            "usar_email": "y",
            "contato_email": "talentos@empresa.com",
            "usar_telefone": "y",
            "contato_telefone": "(27) 98888-2222",
        },
    )

    db.session.refresh(match)
    assert response.status_code == 302
    assert match.contato_email == "talentos@empresa.com"
    assert match.contato_telefone == "(27) 98888-2222"


def test_candidato_ve_contato_do_match_e_estado_aguardando(client):
    contratante, candidato, _, match = criar_match_teste(
        "msg-cand-cont@test.com", "msg-cand-cand@test.com", "Vaga com contato"
    )
    outro_contratante = criar_contratante(email="msg-wait-cont@test.com")
    outra_vaga = criar_vaga(outro_contratante, titulo="Vaga aguardando contato")
    match_sem_mensagem = Match(
        candidato_id=candidato.id,
        contratante_id=outro_contratante.id,
        vaga_id=outra_vaga.id,
        status="ativo",
    )
    db.session.add(match_sem_mensagem)
    match.mensagem_contratante = "Compareça para uma conversa inicial."
    match.contato_email = "contato@empresa.com"
    match.contato_telefone = "(27) 97777-3333"
    db.session.commit()
    login(client, candidato.email)

    response = client.get("/candidato/matches")

    assert response.status_code == 200
    assert b"Ver contato" in response.data
    assert contratante.nome.encode() in response.data
    assert "Compareça para uma conversa inicial.".encode() in response.data
    assert b"mailto:contato@empresa.com" in response.data
    assert "(27) 97777-3333".encode() in response.data
    assert (
        "O contratante ainda não enviou as instruções de contato.".encode()
        in response.data
    )
    assert match_sem_mensagem.id is not None


def test_handlers_403_e_404(client):
    response_404 = client.get("/rota-inexistente")
    assert response_404.status_code == 404

    criar_candidato(email="erro403@test.com")
    login(client, "erro403@test.com")
    response_403 = client.get("/contratante/dashboard")
    assert response_403.status_code == 403
