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
    session,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from trampomatch.extensions import csrf, db
from trampomatch.forms import CurriculoCandidatoForm, PerfilCandidatoForm
from trampomatch.forms.candidato import (
    CATEGORIAS_TRABALHO,
    COORDENADAS_REGIOES,
    DISPONIBILIDADES,
    HABILIDADES_PREDEFINIDAS,
    NIVEIS_EXPERIENCIA,
    REGIOES_GRANDE_VITORIA,
    REGIOES_PROXIMAS,
)
from trampomatch.models import (
    DescarteVaga,
    Interesse,
    InteresseContratante,
    Match,
    PerfilCandidato,
    Vaga,
)
from trampomatch.services import (
    calcular_compatibilidade,
    ordenar_por_recomendacao,
    vaga_compativel,
    verificar_e_criar_match,
)
from trampomatch.services.curriculo import (
    caminho_curriculo,
    limpar_curriculo,
    salvar_curriculo,
)
from trampomatch.services.candidatura import vagas_abertas_para_candidato

bp_candidato = Blueprint("candidato", __name__, url_prefix="/candidato")


def exigir_candidato():
    if not current_user.eh_candidato:
        abort(403)


def quer_json():
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.accept_mimetypes.best == "application/json"
    )


@bp_candidato.route("/novidades/dispensar", methods=["POST"])
@csrf.exempt
@login_required
def dispensar_novidades():
    exigir_candidato()
    current_user.ultimo_acesso_dashboard = datetime.now()
    db.session.commit()
    return "", 204


@bp_candidato.route("/dashboard")
@login_required
def dashboard():
    exigir_candidato()

    perfil = current_user.perfil_candidato

    interesses_ids = {
        i.vaga_id for i in Interesse.query.filter_by(candidato_id=current_user.id).all()
    }
    vagas_disponiveis = vagas_abertas_para_candidato(current_user.id, perfil)

    total_vagas = len(vagas_disponiveis)
    total_interesses = len(interesses_ids)

    # vagas_com_score e contagem calculados apenas sobre vagas elegíveis
    vagas_com_score = []
    vagas_compativeis = 0

    if perfil:
        pares = [(v, calcular_compatibilidade(perfil, v)) for v in vagas_disponiveis]
        pares_ordenados = ordenar_por_recomendacao(pares)
        vagas_compativeis = sum(1 for _, r in pares_ordenados if vaga_compativel(r))
        vagas_com_score = [(v, r) for v, r in pares_ordenados if vaga_compativel(r)][:4]

    # Vagas compatíveis já aceitas (interesses do usuário)
    vagas_aceitas_com_score = []
    compativeis_aceitas = 0
    if perfil and interesses_ids:
        vagas_aceitas = Vaga.query.filter(Vaga.id.in_(interesses_ids)).all()
        pares_aceitas = [
            (v, calcular_compatibilidade(perfil, v)) for v in vagas_aceitas
        ]
        pares_aceitas_ord = ordenar_por_recomendacao(pares_aceitas)
        compativeis_aceitas = sum(1 for _, r in pares_aceitas_ord if vaga_compativel(r))
        vagas_aceitas_com_score = [
            (v, r) for v, r in pares_aceitas_ord if vaga_compativel(r)
        ][:4]

    # ── Totais para KPI cards ─────────────────────────────────────
    total_matches = Match.query.filter_by(
        candidato_id=current_user.id, status="ativo"
    ).count()
    total_convites = InteresseContratante.query.filter_by(
        candidato_id=current_user.id
    ).count()

    # ── Novidades desde o último "Entendido" (só na 1ª visita após login) ──
    if session.pop("show_novidades", False):
        ultima_visita = current_user.ultimo_acesso_dashboard
        if ultima_visita:
            novos_matches = Match.query.filter(
                Match.candidato_id == current_user.id,
                Match.status == "ativo",
                Match.criado_em > ultima_visita,
            ).count()
            novos_convites = InteresseContratante.query.filter(
                InteresseContratante.candidato_id == current_user.id,
                InteresseContratante.criado_em > ultima_visita,
            ).count()
        else:
            novos_matches = 0
            novos_convites = 0
    else:
        novos_matches = 0
        novos_convites = 0

    # Atividades recentes: sem JOIN para não excluir registros com FK não verificada
    interesses_lista = (
        Interesse.query.filter_by(candidato_id=current_user.id)
        .order_by(Interesse.criado_em.desc())
        .limit(8)
        .all()
    )
    descartes_lista = (
        DescarteVaga.query.filter_by(candidato_id=current_user.id)
        .order_by(DescarteVaga.criado_em.desc())
        .limit(8)
        .all()
    )
    atividades_raw = []
    for i in interesses_lista:
        if i.vaga:
            atividades_raw.append(
                {
                    "tipo": "interesse",
                    "titulo": i.vaga.titulo,
                    "vaga_id": i.vaga_id,
                    "criado_em": i.criado_em or datetime.min,
                }
            )
    for d in descartes_lista:
        if d.vaga:
            atividades_raw.append(
                {
                    "tipo": "descarte",
                    "titulo": d.vaga.titulo,
                    "vaga_id": d.vaga_id,
                    "criado_em": d.criado_em or datetime.min,
                }
            )
    atividades_recentes = sorted(
        atividades_raw, key=lambda x: x["criado_em"], reverse=True
    )[:4]

    return render_template(
        "candidato/dashboard.html",
        total_vagas=total_vagas,
        vagas_compativeis=vagas_compativeis,
        compativeis_aceitas=compativeis_aceitas,
        total_interesses=total_interesses,
        perfil=perfil,
        vagas_com_score=vagas_com_score,
        vagas_aceitas_com_score=vagas_aceitas_com_score,
        atividades_recentes=atividades_recentes,
        novos_matches=novos_matches,
        novos_convites=novos_convites,
        total_matches=total_matches,
        total_convites=total_convites,
    )


@bp_candidato.route("/minhas-vagas")
@login_required
def minhas_vagas():
    exigir_candidato()
    interesses = (
        Interesse.query.filter_by(candidato_id=current_user.id)
        .join(Vaga)
        .order_by(Interesse.criado_em.desc())
        .all()
    )
    perfil = current_user.perfil_candidato
    vagas_processadas = []
    for interesse in interesses:
        resultado = (
            calcular_compatibilidade(perfil, interesse.vaga)
            if perfil is not None
            else None
        )
        vagas_processadas.append(
            {
                "interesse": interesse,
                "vaga": interesse.vaga,
                "compatibilidade": resultado.score if resultado is not None else None,
                "resultado_match": (
                    resultado.to_dict() if resultado is not None else None
                ),
            }
        )
    return render_template("candidato/minhas_vagas.html", vagas=vagas_processadas)


@bp_candidato.route("/convites")
@login_required
def convites():
    exigir_candidato()
    perfil = current_user.perfil_candidato
    interesses_ids = db.session.query(Interesse.vaga_id).filter_by(
        candidato_id=current_user.id
    )
    descartes_ids = db.session.query(DescarteVaga.vaga_id).filter_by(
        candidato_id=current_user.id
    )
    interesses_recebidos = (
        InteresseContratante.query.join(Vaga, InteresseContratante.vaga_id == Vaga.id)
        .filter(
            InteresseContratante.candidato_id == current_user.id,
            Vaga.status == "aberta",
            ~InteresseContratante.vaga_id.in_(interesses_ids),
            ~InteresseContratante.vaga_id.in_(descartes_ids),
        )
        .order_by(InteresseContratante.criado_em.desc())
        .all()
    )

    convites_processados = []
    for convite in interesses_recebidos:
        resultado = calcular_compatibilidade(perfil, convite.vaga) if perfil else None
        convites_processados.append(
            {
                "convite": convite,
                "vaga": convite.vaga,
                "contratante": convite.contratante,
                "perfil_contratante": convite.contratante.perfil_contratante,
                "compatibilidade": resultado.score if resultado else None,
                "resultado_match": resultado.to_dict() if resultado else None,
            }
        )

    return render_template("candidato/convites.html", convites=convites_processados)


@bp_candidato.route("/convites/<int:interesse_id>/aceitar", methods=["POST"])
@login_required
def aceitar_convite(interesse_id):
    exigir_candidato()
    convite = InteresseContratante.query.filter_by(
        id=interesse_id, candidato_id=current_user.id
    ).first_or_404()
    if not convite.vaga or convite.vaga.status != "aberta":
        if quer_json():
            return jsonify({"ok": False, "message": "Esta vaga não está aberta."}), 400
        flash("Esta vaga não está aberta para novos interesses.", "warning")
        return redirect(url_for("candidato.convites"))

    DescarteVaga.query.filter_by(
        candidato_id=current_user.id, vaga_id=convite.vaga_id
    ).delete()
    interesse = Interesse.query.filter_by(
        candidato_id=current_user.id, vaga_id=convite.vaga_id
    ).first()
    if interesse is None:
        db.session.add(Interesse(candidato_id=current_user.id, vaga_id=convite.vaga_id))

    try:
        db.session.flush()
        foi_match = verificar_e_criar_match(
            current_user.id, convite.contratante_id, convite.vaga_id
        )
        db.session.commit()
        if quer_json():
            return jsonify(
                {
                    "ok": True,
                    "action": "accept",
                    "convite_id": convite.id,
                    "match": foi_match,
                }
            )
        flash(
            "Convite aceito. É um match!" if foi_match else "Convite aceito.", "success"
        )
    except IntegrityError:
        db.session.rollback()
        if quer_json():
            return jsonify(
                {
                    "ok": True,
                    "action": "accept",
                    "convite_id": convite.id,
                    "match": False,
                }
            )
        flash("Você já demonstrou interesse nesta vaga.", "warning")
    return redirect(url_for("candidato.convites"))


@bp_candidato.route("/convites/<int:interesse_id>/recusar", methods=["POST"])
@login_required
def recusar_convite(interesse_id):
    exigir_candidato()
    convite = InteresseContratante.query.filter_by(
        id=interesse_id, candidato_id=current_user.id
    ).first_or_404()
    if convite.vaga_id is None:
        abort(400)

    Interesse.query.filter_by(
        candidato_id=current_user.id, vaga_id=convite.vaga_id
    ).delete()
    descarte = DescarteVaga.query.filter_by(
        candidato_id=current_user.id, vaga_id=convite.vaga_id
    ).first()
    if descarte is None:
        db.session.add(
            DescarteVaga(candidato_id=current_user.id, vaga_id=convite.vaga_id)
        )

    try:
        db.session.commit()
        if quer_json():
            return jsonify({"ok": True, "action": "skip", "convite_id": convite.id})
        flash("Convite recusado.", "info")
    except IntegrityError:
        db.session.rollback()
        if quer_json():
            return jsonify({"ok": True, "action": "skip", "convite_id": convite.id})
        flash("Este convite já foi recusado.", "warning")
    return redirect(url_for("candidato.convites"))


@bp_candidato.route("/matches")
@login_required
def matches():
    exigir_candidato()
    matches_lista = (
        Match.query.filter_by(candidato_id=current_user.id, status="ativo")
        .order_by(Match.criado_em.desc())
        .all()
    )
    return render_template("candidato/matches.html", matches=matches_lista)


@bp_candidato.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    exigir_candidato()
    perfil_atual = current_user.perfil_candidato
    form = PerfilCandidatoForm(obj=perfil_atual)
    curriculo_form = CurriculoCandidatoForm()
    regiao_base = perfil_atual.regiao if perfil_atual else ""
    regioes_proximas = REGIOES_PROXIMAS.get(regiao_base, [])

    if form.validate_on_submit():
        if perfil_atual is None:
            perfil_atual = PerfilCandidato(usuario_id=current_user.id)
            db.session.add(perfil_atual)

        form.populate_obj(perfil_atual)
        db.session.commit()
        flash("Perfil salvo com sucesso.", "success")
        return redirect(url_for("candidato.dashboard"))

    return render_template(
        "candidato/perfil.html",
        categorias=CATEGORIAS_TRABALHO,
        coordenadas_regioes=COORDENADAS_REGIOES,
        curriculo_form=curriculo_form,
        disponibilidades=DISPONIBILIDADES,
        experiencias=NIVEIS_EXPERIENCIA,
        form=form,
        habilidades_predefinidas=HABILIDADES_PREDEFINIDAS,
        mapa_regioes_proximas=REGIOES_PROXIMAS,
        perfil=perfil_atual,
        regiao_base=regiao_base,
        regioes=REGIOES_GRANDE_VITORIA,
        regioes_proximas=regioes_proximas,
    )


@bp_candidato.route("/perfil/curriculo", methods=["POST"])
@login_required
def enviar_curriculo():
    exigir_candidato()
    perfil_atual = current_user.perfil_candidato
    if perfil_atual is None:
        flash("Complete seu perfil antes de enviar o currículo.", "warning")
        return redirect(url_for("candidato.perfil"))

    form = CurriculoCandidatoForm()
    if form.validate_on_submit():
        salvar_curriculo(perfil_atual, form.curriculo.data)
        db.session.commit()
        flash("Currículo enviado com sucesso.", "success")
    else:
        for erros in form.errors.values():
            for erro in erros:
                flash(erro, "danger")
    return redirect(url_for("candidato.perfil"))


@bp_candidato.route("/perfil/curriculo/remover", methods=["POST"])
@login_required
def remover_curriculo():
    exigir_candidato()
    perfil_atual = current_user.perfil_candidato
    if perfil_atual and perfil_atual.curriculo_arquivo:
        limpar_curriculo(perfil_atual)
        db.session.commit()
        flash("Currículo removido.", "info")
    return redirect(url_for("candidato.perfil"))


@bp_candidato.route("/perfil/curriculo")
@login_required
def baixar_curriculo():
    exigir_candidato()
    perfil_atual = current_user.perfil_candidato
    if not perfil_atual or not perfil_atual.curriculo_arquivo:
        abort(404)

    caminho = caminho_curriculo(perfil_atual.curriculo_arquivo)
    if not caminho or not caminho.exists():
        abort(404)

    return send_file(
        caminho,
        as_attachment=True,
        download_name=perfil_atual.curriculo_nome_original or "curriculo",
    )


@bp_candidato.route("/perfil/curriculo/visualizar")
@login_required
def visualizar_curriculo():
    exigir_candidato()
    perfil_atual = current_user.perfil_candidato
    if not perfil_atual or not perfil_atual.curriculo_arquivo:
        abort(404)

    caminho = caminho_curriculo(perfil_atual.curriculo_arquivo)
    if not caminho or not caminho.exists():
        abort(404)

    return send_file(
        caminho,
        as_attachment=False,
        download_name=perfil_atual.curriculo_nome_original or "curriculo",
    )
