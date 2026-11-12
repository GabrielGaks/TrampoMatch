from datetime import datetime

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from trampomatch.extensions import db
from trampomatch.forms import (
    FiltroCandidatoForm,
    GoogleContratanteOnboardingForm,
    MensagemMatchForm,
    VagaForm,
)
from trampomatch.forms.auth import AREAS_ATUACAO_PREDEFINIDAS, normalizar_areas_atuacao
from trampomatch.forms.candidato import (
    CATEGORIAS_TRABALHO,
    COORDENADAS_REGIOES,
    REGIOES_GRANDE_VITORIA,
)
from trampomatch.models import (
    DescarteContratante,
    Habilidade,
    Interesse,
    InteresseContratante,
    Match,
    PerfilCandidato,
    PerfilContratante,
    RecusaCandidaturaVaga,
    Usuario,
    Vaga,
)
from trampomatch.services import calcular_compatibilidade, verificar_e_criar_match
from trampomatch.services.candidatura import (
    contar_interessados_pendentes,
    query_interessados_pendentes,
)
from trampomatch.services.curriculo import caminho_curriculo
from trampomatch.views.auth import _salvar_logo_empresa

bp_contratante = Blueprint("contratante", __name__, url_prefix="/contratante")


def exigir_contratante():
    if not current_user.eh_contratante:
        abort(403)


def vaga_do_usuario(id):
    vaga = db.get_or_404(Vaga, id)
    if vaga.contratante_id != current_user.id:
        abort(403)
    return vaga


def quer_json():
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.accept_mimetypes.best == "application/json"
    )


@bp_contratante.route("/dashboard")
@login_required
def dashboard():
    exigir_contratante()

    def _rel(dt):
        if not dt:
            return ""
        delta = datetime.now() - dt
        if delta.days == 0:
            return f"Hoje, {dt.strftime('%H:%M')}"
        if delta.days == 1:
            return f"Ontem, {dt.strftime('%H:%M')}"
        return f"Há {delta.days} dias"

    vagas = (
        Vaga.query.filter_by(contratante_id=current_user.id)
        .order_by(Vaga.criado_em.desc())
        .all()
    )
    vagas_abertas_list = [v for v in vagas if v.status == "aberta"]

    total_interessados = sum(
        contar_interessados_pendentes(v.id, current_user.id) for v in vagas
    )
    total_matches = Match.query.filter_by(
        contratante_id=current_user.id, status="ativo"
    ).count()
    total_candidatos = (
        PerfilCandidato.query.join(Usuario, PerfilCandidato.usuario_id == Usuario.id)
        .filter(Usuario.ativo.is_(True))
        .count()
    )
    total_curtidos = InteresseContratante.query.filter_by(
        contratante_id=current_user.id
    ).count()

    # Candidatos compatíveis agrupados por vaga aberta
    candidatos_por_vaga = (
        _top_candidatos_por_vaga(
            vagas_abertas_list,
            current_user.id,
            limite_vagas=3,
            limite_por_vaga=2,
        )
        if vagas_abertas_list
        else []
    )

    # Feed de atividades recentes (interesses + matches + vagas)
    atividades = []
    for i in (
        Interesse.query.join(Vaga)
        .filter(Vaga.contratante_id == current_user.id)
        .order_by(Interesse.criado_em.desc())
        .limit(5)
        .all()
    ):
        atividades.append(
            {
                "tipo": "interesse",
                "descricao": f"{i.candidato.nome} demonstrou interesse na vaga {i.vaga.titulo}",
                "tempo": _rel(i.criado_em),
                "criado_em": i.criado_em,
            }
        )
    for m in (
        Match.query.filter_by(contratante_id=current_user.id)
        .order_by(Match.criado_em.desc())
        .limit(3)
        .all()
    ):
        atividades.append(
            {
                "tipo": "match",
                "descricao": f"{m.candidato.nome} foi compatível com uma das suas vagas",
                "tempo": _rel(m.criado_em),
                "criado_em": m.criado_em,
            }
        )
    for v in vagas[:3]:
        atividades.append(
            {
                "tipo": "vaga",
                "descricao": f"Vaga {v.titulo} foi publicada",
                "tempo": _rel(v.criado_em),
                "criado_em": v.criado_em,
            }
        )
    atividades.sort(key=lambda x: x["criado_em"] or datetime.min, reverse=True)
    atividades = atividades[:5]

    return render_template(
        "contratante/dashboard.html",
        perfil=current_user.perfil_contratante,
        primeiro_nome=current_user.nome.split()[0],
        total_vagas=len(vagas),
        vagas_abertas=sum(1 for v in vagas if v.status == "aberta"),
        vagas_encerradas=sum(1 for v in vagas if v.status == "encerrada"),
        total_interessados=total_interessados,
        total_matches=total_matches,
        total_candidatos=total_candidatos,
        total_curtidos=total_curtidos,
        vagas_recentes=vagas[:3],
        candidatos_por_vaga=candidatos_por_vaga,
        atividades=atividades,
        agora=datetime.now(),
    )


@bp_contratante.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    exigir_contratante()
    perfil_atual = current_user.perfil_contratante
    form = GoogleContratanteOnboardingForm(obj=perfil_atual)

    if form.validate_on_submit():
        if perfil_atual is None:
            perfil_atual = PerfilContratante(usuario_id=current_user.id)
            db.session.add(perfil_atual)

        perfil_atual.nome_empresa = form.nome_empresa.data.strip()
        perfil_atual.regiao = form.regiao.data.strip()
        perfil_atual.descricao = form.descricao.data.strip()
        perfil_atual.tipo_contratante = form.tipo_contratante.data
        perfil_atual.quantidade_funcionarios = form.quantidade_funcionarios.data
        perfil_atual.areas_atuacao = normalizar_areas_atuacao(form.areas_atuacao.data)
        perfil_atual.site = (form.site.data or "").strip() or None

        logo = _salvar_logo_empresa(form.logo_empresa.data)
        if logo:
            perfil_atual.logo_empresa = logo

        db.session.commit()
        flash("Perfil salvo com sucesso.", "success")
        return redirect(url_for("contratante.dashboard"))

    return render_template(
        "auth/google_onboarding.html",
        form=form,
        perfil=perfil_atual,
        nome=current_user.nome,
        primeiro_nome=current_user.nome.split()[0],
        tipo_perfil="contratante",
        percentual_base=perfil_atual.percentual_completo if perfil_atual else 40,
        regioes=REGIOES_GRANDE_VITORIA,
        coordenadas_regioes=COORDENADAS_REGIOES,
        habilidades_predefinidas=[],
        areas_atuacao_predefinidas=AREAS_ATUACAO_PREDEFINIDAS,
    )


@bp_contratante.route("/vagas")
@login_required
def minhas_vagas():
    exigir_contratante()
    vagas = (
        Vaga.query.filter_by(contratante_id=current_user.id)
        .order_by(Vaga.criado_em.desc())
        .all()
    )
    contadores = {
        v.id: contar_interessados_pendentes(v.id, current_user.id) for v in vagas
    }
    return render_template("contratante/minhas_vagas.html", vagas=vagas, contadores=contadores)


@bp_contratante.route("/vagas/nova", methods=["GET", "POST"])
@login_required
def nova_vaga():
    exigir_contratante()
    if current_user.perfil_contratante is None:
        flash(
            "Complete seu perfil de contratante antes de publicar uma vaga.", "warning"
        )
        return redirect(url_for("contratante.perfil"))

    form = VagaForm()
    if form.validate_on_submit():
        vaga = Vaga(contratante_id=current_user.id)
        form.populate_obj(vaga)
        db.session.add(vaga)
        db.session.commit()
        flash("Vaga cadastrada com sucesso.", "success")
        return redirect(url_for("contratante.minhas_vagas"))
    return render_template(
        "contratante/vaga_form.html",
        form=form,
        titulo="Nova vaga",
        regioes=REGIOES_GRANDE_VITORIA,
        coordenadas_regioes=COORDENADAS_REGIOES,
        habilidades_predefinidas=[
            h.nome for h in Habilidade.query.order_by(Habilidade.nome).all()
        ],
    )


@bp_contratante.route("/vagas/<int:id>/editar", methods=["GET", "POST"])
@login_required
def editar_vaga(id):
    exigir_contratante()
    vaga = vaga_do_usuario(id)
    form = VagaForm(obj=vaga)
    if form.validate_on_submit():
        form.populate_obj(vaga)
        db.session.commit()
        flash("Vaga atualizada com sucesso.", "success")
        return redirect(url_for("contratante.minhas_vagas"))
    return render_template(
        "contratante/vaga_form.html",
        form=form,
        titulo="Editar vaga",
        regioes=REGIOES_GRANDE_VITORIA,
        coordenadas_regioes=COORDENADAS_REGIOES,
        habilidades_predefinidas=[
            h.nome for h in Habilidade.query.order_by(Habilidade.nome).all()
        ],
    )


@bp_contratante.route("/vagas/<int:id>/encerrar", methods=["POST"])
@login_required
def encerrar_vaga(id):
    exigir_contratante()
    vaga = vaga_do_usuario(id)
    vaga.status = "encerrada"
    db.session.commit()
    flash("Vaga encerrada com sucesso.", "success")
    return redirect(url_for("contratante.minhas_vagas"))


@bp_contratante.route("/vagas/<int:id>/interessados")
@login_required
def interessados(id):
    exigir_contratante()
    vaga = vaga_do_usuario(id)
    interesses = (
        query_interessados_pendentes(vaga.id, current_user.id)
        .order_by(Interesse.criado_em.desc())
        .all()
    )
    candidatos = []
    for interesse in interesses:
        perfil = interesse.candidato.perfil_candidato
        resultado = calcular_compatibilidade(perfil, vaga) if perfil else None
        candidatos.append(
            {
                "interesse": interesse,
                "usuario": interesse.candidato,
                "perfil": perfil,
                "compatibilidade": resultado.score if resultado else None,
                "resultado_match": resultado.to_dict() if resultado else None,
            }
        )
    candidatos.sort(
        key=lambda x: (x["compatibilidade"] is None, -(x["compatibilidade"] or 0))
    )
    return render_template(
        "contratante/interessados.html", vaga=vaga, candidatos=candidatos
    )


@bp_contratante.route(
    "/vagas/<int:id>/interessados/<int:candidato_id>/aceitar", methods=["POST"]
)
@login_required
def aceitar_interessado(id, candidato_id):
    exigir_contratante()
    vaga = vaga_do_usuario(id)
    candidato = db.get_or_404(Usuario, candidato_id)
    if not candidato.eh_candidato:
        abort(400)
    if vaga.status != "aberta":
        if quer_json():
            return jsonify({"ok": False, "message": "Esta vaga não está aberta."}), 400
        flash("Esta vaga não está aberta para novos interesses.", "warning")
        return redirect(url_for("contratante.interessados", id=vaga.id))

    interesse_candidato = Interesse.query.filter_by(
        candidato_id=candidato_id, vaga_id=vaga.id
    ).first_or_404()
    DescarteContratante.query.filter_by(
        contratante_id=current_user.id, candidato_id=candidato_id
    ).delete()
    ja_existe = InteresseContratante.query.filter_by(
        contratante_id=current_user.id, candidato_id=candidato_id, vaga_id=vaga.id
    ).first()
    if ja_existe is None:
        db.session.add(
            InteresseContratante(
                contratante_id=current_user.id,
                candidato_id=interesse_candidato.candidato_id,
                vaga_id=vaga.id,
            )
        )

    try:
        db.session.flush()
        foi_match = verificar_e_criar_match(candidato_id, current_user.id, vaga.id)
        db.session.commit()
        if quer_json():
            return jsonify(
                {
                    "ok": True,
                    "action": "like",
                    "candidato_id": candidato_id,
                    "match": foi_match,
                }
            )
        flash(
            (
                f"É um match com {candidato.nome}!"
                if foi_match
                else "Interesse registrado."
            ),
            "success",
        )
    except IntegrityError:
        db.session.rollback()
        if quer_json():
            return jsonify(
                {
                    "ok": True,
                    "action": "like",
                    "candidato_id": candidato_id,
                    "match": False,
                }
            )
        flash("Interesse já registrado.", "warning")
    return redirect(url_for("contratante.interessados", id=vaga.id))


@bp_contratante.route(
    "/vagas/<int:id>/interessados/<int:candidato_id>/recusar", methods=["POST"]
)
@login_required
def recusar_interessado(id, candidato_id):
    exigir_contratante()
    vaga = vaga_do_usuario(id)
    db.get_or_404(Usuario, candidato_id)
    Interesse.query.filter_by(candidato_id=candidato_id, vaga_id=vaga.id).delete()
    InteresseContratante.query.filter_by(
        contratante_id=current_user.id, candidato_id=candidato_id, vaga_id=vaga.id
    ).delete()
    descarte = DescarteContratante.query.filter_by(
        contratante_id=current_user.id, candidato_id=candidato_id
    ).first()
    if descarte is None:
        db.session.add(
            DescarteContratante(
                contratante_id=current_user.id, candidato_id=candidato_id
            )
        )
    recusa = RecusaCandidaturaVaga.query.filter_by(
        candidato_id=candidato_id, vaga_id=vaga.id
    ).first()
    if recusa is None:
        db.session.add(
            RecusaCandidaturaVaga(
                candidato_id=candidato_id,
                vaga_id=vaga.id,
                contratante_id=current_user.id,
            )
        )

    try:
        db.session.commit()
        if quer_json():
            return jsonify({"ok": True, "action": "skip", "candidato_id": candidato_id})
        flash(
            "Candidato recusado. Ele não poderá se candidatar novamente a esta vaga.",
            "info",
        )
    except IntegrityError:
        db.session.rollback()
        if quer_json():
            return jsonify({"ok": True, "action": "skip", "candidato_id": candidato_id})
        flash("Este candidato já foi recusado.", "warning")
    return redirect(url_for("contratante.interessados", id=vaga.id))


# ── Candidatos ──────────────────────────────────────────────────────────────


def categorias_filtro_candidatos(vaga_selecionada, vagas_abertas) -> set[str]:
    if vaga_selecionada and vaga_selecionada.categoria:
        return {vaga_selecionada.categoria}
    return {v.categoria for v in vagas_abertas if v.categoria}


def rotulos_categorias(slugs: set[str]) -> list[str]:
    mapa = dict(CATEGORIAS_TRABALHO)
    return [mapa[slug] for slug in sorted(slugs) if slug in mapa]


def _perfis_elegiveis_para_vaga(vaga, contratante_id) -> list[PerfilCandidato]:
    interesses_ids = db.session.query(InteresseContratante.candidato_id).filter_by(
        contratante_id=contratante_id,
        vaga_id=vaga.id,
    )
    descartes_ids = db.session.query(DescarteContratante.candidato_id).filter_by(
        contratante_id=contratante_id
    )
    query = PerfilCandidato.query.join(
        Usuario, PerfilCandidato.usuario_id == Usuario.id
    ).filter(
        Usuario.ativo.is_(True),
        ~PerfilCandidato.usuario_id.in_(interesses_ids),
        ~PerfilCandidato.usuario_id.in_(descartes_ids),
    )
    if vaga.categoria:
        query = query.filter(PerfilCandidato.categoria == vaga.categoria)
    return query.all()


def _top_candidatos_por_vaga(
    vagas_abertas,
    contratante_id,
    *,
    limite_vagas: int = 3,
    limite_por_vaga: int = 2,
) -> list[dict]:
    grupos = []
    for vaga in vagas_abertas:
        pares = [
            (perfil, calcular_compatibilidade(perfil, vaga).score)
            for perfil in _perfis_elegiveis_para_vaga(vaga, contratante_id)
        ]
        pares.sort(key=lambda item: -item[1])
        candidatos = [
            {
                "perfil": perfil,
                "usuario": perfil.usuario,
                "score": score,
                "habilidades": perfil.habilidades_lista()[:2],
            }
            for perfil, score in pares[:limite_por_vaga]
        ]
        if not candidatos:
            continue
        grupos.append({"vaga": vaga, "candidatos": candidatos})

    grupos.sort(key=lambda grupo: -grupo["candidatos"][0]["score"])
    return grupos[:limite_vagas]


@bp_contratante.route("/candidatos")
@login_required
def candidatos():
    exigir_contratante()

    form = FiltroCandidatoForm(request.args, meta={"csrf": False})
    ordenar = request.args.get("ordenar", "compatibilidade").strip()
    if ordenar not in {"compatibilidade", "recentes"}:
        ordenar = "compatibilidade"

    vagas_abertas = (
        Vaga.query.filter_by(contratante_id=current_user.id, status="aberta")
        .order_by(Vaga.criado_em.desc())
        .all()
    )

    # Vaga selecionada para avaliação
    vaga_id = request.args.get("vaga_id", type=int)
    vaga_selecionada = None
    if vaga_id:
        vaga_selecionada = Vaga.query.filter_by(
            id=vaga_id, contratante_id=current_user.id, status="aberta"
        ).first()

    # Exclui candidatos já curtidos para esta vaga específica (se vaga selecionada)
    # ou todos os curtidos sem vaga (comportamento legado)
    if vaga_selecionada:
        interesses_ids = db.session.query(InteresseContratante.candidato_id).filter_by(
            contratante_id=current_user.id, vaga_id=vaga_selecionada.id
        )
    else:
        interesses_ids = db.session.query(InteresseContratante.candidato_id).filter_by(
            contratante_id=current_user.id
        )

    descartes_ids = db.session.query(DescarteContratante.candidato_id).filter_by(
        contratante_id=current_user.id
    )

    query = PerfilCandidato.query.join(
        Usuario, PerfilCandidato.usuario_id == Usuario.id
    ).filter(
        Usuario.ativo.is_(True),
        ~PerfilCandidato.usuario_id.in_(interesses_ids),
        ~PerfilCandidato.usuario_id.in_(descartes_ids),
    )

    categorias_filtro_ativas = categorias_filtro_candidatos(vaga_selecionada, vagas_abertas)
    if categorias_filtro_ativas:
        query = query.filter(PerfilCandidato.categoria.in_(categorias_filtro_ativas))
    categorias_filtro_labels = rotulos_categorias(categorias_filtro_ativas)

    regiao = request.args.get("regiao", "").strip()
    tipo_trabalho = request.args.get("tipo_trabalho", "").strip()
    if regiao:
        query = query.filter(PerfilCandidato.regiao.ilike(f"%{regiao}%"))
    if tipo_trabalho:
        query = query.filter(PerfilCandidato.tipo_trabalho == tipo_trabalho)

    perfis = query.order_by(PerfilCandidato.id.desc()).all()

    # Calcula score contra a vaga selecionada; se nenhuma, usa a melhor entre as abertas
    vaga_para_score = [vaga_selecionada] if vaga_selecionada else vagas_abertas
    candidatos_processados = []
    for perfil in perfis:
        if vaga_para_score:
            resultados = [calcular_compatibilidade(perfil, v) for v in vaga_para_score]
            melhor = max(resultados, key=lambda r: r.score)
        else:
            melhor = None
        candidatos_processados.append(
            {
                "perfil": perfil,
                "usuario": perfil.usuario,
                "compatibilidade": melhor.score if melhor else None,
                "resultado_match": melhor.to_dict() if melhor else None,
            }
        )

    if ordenar == "compatibilidade" and vaga_para_score:
        candidatos_processados.sort(
            key=lambda x: (x["compatibilidade"] is None, -(x["compatibilidade"] or 0))
        )

    return render_template(
        "contratante/candidatos.html",
        form=form,
        candidatos=candidatos_processados,
        ordenar=ordenar,
        vagas_abertas=vagas_abertas,
        vaga_selecionada=vaga_selecionada,
        categorias_filtro_ativas=categorias_filtro_ativas,
        categorias_filtro_labels=categorias_filtro_labels,
        regioes=REGIOES_GRANDE_VITORIA,
        coordenadas_regioes=COORDENADAS_REGIOES,
    )


@bp_contratante.route("/candidatos/respondidos")
@login_required
def candidatos_respondidos():
    exigir_contratante()

    interesses = (
        InteresseContratante.query.filter_by(contratante_id=current_user.id)
        .order_by(
            InteresseContratante.vaga_id.asc(), InteresseContratante.criado_em.desc()
        )
        .all()
    )

    curtidos = []
    for ic in interesses:
        pc = ic.candidato.perfil_candidato
        score = None
        resultado_match = None
        if pc and ic.vaga:
            resultado_match = calcular_compatibilidade(pc, ic.vaga)
            score = round(resultado_match.score, 1)
        foi_match = (
            Match.query.filter_by(
                candidato_id=ic.candidato_id,
                contratante_id=current_user.id,
                vaga_id=ic.vaga_id,
                status="ativo",
            ).first()
            is not None
        )
        curtidos.append(
            {
                "usuario": ic.candidato,
                "perfil": pc,
                "score": score,
                "resultado_match": resultado_match.to_dict()
                if resultado_match
                else None,
                "match": foi_match,
                "vaga": ic.vaga,
                "vaga_id": ic.vaga_id,
            }
        )

    # Agrupamento por vaga para exibição
    curtidos_por_vaga: dict[str, list] = {}
    for item in curtidos:
        chave = item["vaga"].titulo if item["vaga"] else "Sem vaga"
        curtidos_por_vaga.setdefault(chave, []).append(item)

    descartes = (
        DescarteContratante.query.filter_by(contratante_id=current_user.id)
        .order_by(DescarteContratante.criado_em.desc())
        .all()
    )
    descartados = [
        {
            "usuario": d.candidato,
            "perfil": d.candidato.perfil_candidato,
        }
        for d in descartes
    ]

    return render_template(
        "contratante/candidatos_respondidos.html",
        curtidos=curtidos,
        curtidos_por_vaga=curtidos_por_vaga,
        descartados=descartados,
    )


@bp_contratante.route("/candidatos/<int:id>/curriculo")
@login_required
def baixar_curriculo_candidato(id):
    exigir_contratante()
    candidato = db.get_or_404(Usuario, id)
    if not candidato.eh_candidato or not candidato.perfil_candidato:
        abort(404)

    perfil = candidato.perfil_candidato
    if not perfil.curriculo_arquivo:
        abort(404)

    caminho = caminho_curriculo(perfil.curriculo_arquivo)
    if not caminho or not caminho.exists():
        abort(404)

    return send_file(
        caminho,
        as_attachment=True,
        download_name=perfil.curriculo_nome_original or "curriculo",
    )


@bp_contratante.route("/candidatos/<int:id>/curriculo/visualizar")
@login_required
def visualizar_curriculo_candidato(id):
    exigir_contratante()
    candidato = db.get_or_404(Usuario, id)
    if not candidato.eh_candidato or not candidato.perfil_candidato:
        abort(404)

    perfil = candidato.perfil_candidato
    if not perfil.curriculo_arquivo:
        abort(404)

    caminho = caminho_curriculo(perfil.curriculo_arquivo)
    if not caminho or not caminho.exists():
        abort(404)

    return send_file(
        caminho,
        as_attachment=False,
        download_name=perfil.curriculo_nome_original or "curriculo",
    )


@bp_contratante.route("/candidatos/<int:id>/remover-interesse", methods=["POST"])
@login_required
def remover_interesse_candidato(id):
    exigir_contratante()
    InteresseContratante.query.filter_by(
        contratante_id=current_user.id, candidato_id=id
    ).delete()
    db.session.commit()
    flash("Interesse removido. O candidato voltou para a fila.", "info")
    return redirect(url_for("contratante.candidatos_respondidos"))


@bp_contratante.route("/candidatos/<int:id>/restaurar", methods=["POST"])
@login_required
def restaurar_candidato(id):
    exigir_contratante()
    DescarteContratante.query.filter_by(
        contratante_id=current_user.id, candidato_id=id
    ).delete()
    db.session.commit()
    flash("Candidato restaurado. Ele aparecerá novamente na fila.", "success")
    return redirect(url_for("contratante.candidatos_respondidos"))


@bp_contratante.route("/candidatos/<int:id>/interesse", methods=["POST"])
@login_required
def interesse_candidato(id):
    exigir_contratante()
    candidato = db.get_or_404(Usuario, id)
    if not candidato.eh_candidato:
        abort(400)

    # vaga_id pode vir do form (HTML) ou do body JSON
    vaga_id_raw = request.form.get("vaga_id") or (
        request.get_json(silent=True) or {}
    ).get("vaga_id")
    vaga_id = int(vaga_id_raw) if vaga_id_raw else None

    # Valida que a vaga pertence ao contratante
    if vaga_id:
        vaga_valida = Vaga.query.filter_by(
            id=vaga_id, contratante_id=current_user.id, status="aberta"
        ).first()
        if not vaga_valida:
            vaga_id = None

    DescarteContratante.query.filter_by(
        contratante_id=current_user.id, candidato_id=id
    ).delete()

    # Verifica duplicata antes de inserir (evita IntegrityError com constraint legada no SQLite)
    ja_existe = InteresseContratante.query.filter_by(
        contratante_id=current_user.id, candidato_id=id, vaga_id=vaga_id
    ).first()
    if ja_existe:
        if quer_json():
            return jsonify(
                {"ok": True, "action": "like", "candidato_id": id, "match": False}
            )
        return redirect(url_for("contratante.candidatos", vaga_id=vaga_id))

    interesse = InteresseContratante(
        contratante_id=current_user.id, candidato_id=id, vaga_id=vaga_id
    )
    db.session.add(interesse)
    try:
        db.session.flush()
        foi_match = verificar_e_criar_match(id, current_user.id, vaga_id)
        db.session.commit()
        if quer_json():
            return jsonify(
                {"ok": True, "action": "like", "candidato_id": id, "match": foi_match}
            )
        if foi_match:
            flash(f"É um match com {candidato.nome}!", "success")
        else:
            flash(f"Interesse em {candidato.nome} registrado.", "success")
    except IntegrityError:
        db.session.rollback()
        if quer_json():
            return jsonify(
                {"ok": True, "action": "like", "candidato_id": id, "match": False}
            )
    return redirect(url_for("contratante.candidatos", vaga_id=vaga_id))


@bp_contratante.route("/candidatos/<int:id>/descartar", methods=["POST"])
@login_required
def descartar_candidato(id):
    exigir_contratante()
    db.get_or_404(Usuario, id)

    InteresseContratante.query.filter_by(
        contratante_id=current_user.id, candidato_id=id
    ).delete()
    descarte = DescarteContratante(contratante_id=current_user.id, candidato_id=id)
    db.session.add(descarte)
    try:
        db.session.commit()
        if quer_json():
            return jsonify({"ok": True, "action": "skip", "candidato_id": id})
    except IntegrityError:
        db.session.rollback()
        if quer_json():
            return jsonify({"ok": True, "action": "skip", "candidato_id": id})
    return redirect(url_for("contratante.candidatos"))


@bp_contratante.route("/habilidades/nova", methods=["POST"])
@login_required
def nova_habilidade():
    exigir_contratante()
    data = request.get_json(silent=True) or {}
    nome = data.get("nome", "").strip()[:100]
    if not nome:
        return jsonify(error="Nome inválido"), 400
    existing = Habilidade.query.filter(
        db.func.lower(Habilidade.nome) == nome.lower()
    ).first()
    if existing:
        return jsonify(nome=existing.nome)
    hab = Habilidade(nome=nome)
    db.session.add(hab)
    try:
        db.session.commit()
        return jsonify(nome=hab.nome), 201
    except Exception:
        db.session.rollback()
        return jsonify(nome=nome)


@bp_contratante.route("/matches")
@login_required
def matches():
    exigir_contratante()
    matches_lista = (
        Match.query.filter_by(contratante_id=current_user.id, status="ativo")
        .order_by(Match.criado_em.desc())
        .all()
    )
    return render_template("contratante/matches.html", matches=matches_lista)


@bp_contratante.route("/matches/<int:match_id>/mensagem", methods=["GET", "POST"])
@login_required
def mensagem_match(match_id):
    exigir_contratante()
    match = Match.query.filter_by(
        id=match_id, contratante_id=current_user.id, status="ativo"
    ).first_or_404()
    form = MensagemMatchForm()

    if request.method == "GET":
        form.mensagem.data = match.mensagem_contratante or ""
        form.usar_email.data = bool(match.contato_email)
        form.contato_email.data = match.contato_email or ""
        form.usar_telefone.data = bool(match.contato_telefone)
        form.contato_telefone.data = match.contato_telefone or ""

    if form.validate_on_submit():
        match.mensagem_contratante = form.mensagem.data.strip()
        match.contato_email = form.contato_email.data or None
        match.contato_telefone = form.contato_telefone.data or None
        match.mensagem_enviada_em = datetime.now()
        db.session.commit()
        flash("Mensagem do match salva com sucesso.", "success")
        return redirect(url_for("contratante.matches"))

    return render_template(
        "contratante/mensagem_match.html",
        form=form,
        match=match,
    )
