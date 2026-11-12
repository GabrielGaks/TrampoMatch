from flask import Blueprint, abort, flash, jsonify
from flask import redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from trampomatch.extensions import db
from trampomatch.forms import FiltroVagaForm
from trampomatch.forms.candidato import (
    CATEGORIAS_TRABALHO,
    COORDENADAS_REGIOES,
    REGIOES_GRANDE_VITORIA,
)
from trampomatch.models import DescarteVaga, Interesse, RecusaCandidaturaVaga, Vaga
from trampomatch.models.vaga import COMPLEXIDADE_CATEGORIAS
from trampomatch.services import (
    calcular_compatibilidade,
    ordenar_por_recomendacao,
    verificar_e_criar_match,
)
from trampomatch.services.candidatura import candidato_bloqueado_para_vaga

bp_vagas = Blueprint("vagas", __name__, url_prefix="/vagas")


def quer_json():
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.accept_mimetypes.best == "application/json"
    )


def exigir_candidato():
    if not current_user.eh_candidato:
        abort(403)


def perfil_candidato_obrigatorio():
    perfil = current_user.perfil_candidato
    if perfil is None:
        flash("Complete seu perfil antes de buscar vagas compatíveis.", "warning")
        return None
    return perfil


def aplicar_filtros(query, categoria_default=""):
    regiao = request.args.get("regiao", "").strip()
    # Usa categoria_default (perfil do candidato) só se não vier param na URL
    categoria = (
        request.args["categoria"].strip()
        if "categoria" in request.args
        else categoria_default
    )
    tipo_vaga = request.args.get("tipo_vaga", "").strip()
    status = request.args.get("status", "").strip()
    complexidade = request.args.get("complexidade", "").strip()

    if regiao:
        query = query.filter(Vaga.regiao.ilike(f"%{regiao}%"))
    if categoria:
        query = query.filter(Vaga.categoria == categoria)
    if tipo_vaga:
        query = query.filter(Vaga.tipo_vaga == tipo_vaga)
    if status:
        query = query.filter(Vaga.status == status)
    else:
        query = query.filter(Vaga.status == "aberta")
    if complexidade:
        cat = next(
            (item for item in COMPLEXIDADE_CATEGORIAS if item["slug"] == complexidade),
            None,
        )
        if cat is not None:
            query = query.filter(
                Vaga.complexidade >= cat["min"],
                Vaga.complexidade <= cat["max"],
            )
    return query


@bp_vagas.route("/")
@login_required
def listagem():
    perfil = current_user.perfil_candidato if current_user.eh_candidato else None
    if current_user.eh_candidato and perfil is None:
        flash("Complete seu perfil antes de buscar vagas compatíveis.", "warning")
        return redirect(url_for("candidato.perfil"))

    # Categoria padrão = categoria do perfil; pode ser sobrescrita via URL (?categoria=)
    categoria_default = (perfil.categoria or "") if perfil else ""
    categoria_ativa = (
        request.args["categoria"].strip()
        if "categoria" in request.args
        else categoria_default
    )

    form = FiltroVagaForm(request.args, meta={"csrf": False})
    ordenar = request.args.get("ordenar", "compatibilidade").strip()
    if ordenar not in {"compatibilidade", "recentes"}:
        ordenar = "compatibilidade"

    query = aplicar_filtros(Vaga.query, categoria_ativa).order_by(Vaga.criado_em.desc())

    if current_user.eh_candidato:
        query = query.filter(
            ~Vaga.id.in_(
                db.session.query(Interesse.vaga_id).filter_by(
                    candidato_id=current_user.id
                )
            ),
            ~Vaga.id.in_(
                db.session.query(DescarteVaga.vaga_id).filter_by(
                    candidato_id=current_user.id
                )
            ),
            ~Vaga.id.in_(
                db.session.query(RecusaCandidaturaVaga.vaga_id).filter_by(
                    candidato_id=current_user.id
                )
            ),
        )

    vagas = query.all()
    pares_recomendacao = []
    for vaga in vagas:
        resultado = (
            calcular_compatibilidade(perfil, vaga) if perfil is not None else None
        )
        if resultado is not None:
            pares_recomendacao.append((vaga, resultado))
            continue

        pares_recomendacao.append((vaga, None))

    if perfil is not None and ordenar == "compatibilidade":
        pares_recomendacao = ordenar_por_recomendacao(pares_recomendacao)

    vagas_processadas = []
    for vaga, resultado in pares_recomendacao:
        vagas_processadas.append(
            {
                "vaga": vaga,
                "compatibilidade": resultado.score if resultado is not None else None,
                "resultado_match": (
                    resultado.to_dict() if resultado is not None else None
                ),
            }
        )
    # Label da categoria ativa (para exibir no indicador de filtro)
    categoria_ativa_label = next(
        (label for slug, label in CATEGORIAS_TRABALHO if slug == categoria_ativa),
        None,
    )

    return render_template(
        "vagas/listagem.html",
        form=form,
        ordenar=ordenar,
        vagas=vagas_processadas,
        regioes=REGIOES_GRANDE_VITORIA,
        coordenadas_regioes=COORDENADAS_REGIOES,
        categorias=CATEGORIAS_TRABALHO,
        categoria_ativa=categoria_ativa,
        categoria_ativa_label=categoria_ativa_label,
    )


@bp_vagas.route("/<int:id>")
@login_required
def detalhe(id):
    vaga = db.get_or_404(Vaga, id)
    compatibilidade = None
    tem_interesse = False
    candidatura_bloqueada = False
    if current_user.eh_candidato:
        perfil = perfil_candidato_obrigatorio()
        if perfil is None:
            return redirect(url_for("candidato.perfil"))
        resultado = calcular_compatibilidade(perfil, vaga)
        compatibilidade = resultado.score
        tem_interesse = (
            Interesse.query.filter_by(
                candidato_id=current_user.id, vaga_id=vaga.id
            ).first()
            is not None
        )
        candidatura_bloqueada = candidato_bloqueado_para_vaga(
            current_user.id, vaga.id
        )
    return render_template(
        "vagas/detalhe.html",
        vaga=vaga,
        compatibilidade=compatibilidade,
        resultado_match=resultado.to_dict() if current_user.eh_candidato else None,
        tem_interesse=tem_interesse,
        candidatura_bloqueada=candidatura_bloqueada,
    )


@bp_vagas.route("/<int:id>/interesse", methods=["POST"])
@login_required
def demonstrar_interesse(id):
    exigir_candidato()
    if perfil_candidato_obrigatorio() is None:
        return redirect(url_for("candidato.perfil"))
    vaga = db.get_or_404(Vaga, id)
    if vaga.status != "aberta":
        if quer_json():
            return jsonify({"ok": False, "message": "Esta vaga não está aberta."}), 400
        flash("Esta vaga não está aberta para novos interesses.", "warning")
        return redirect(url_for("vagas.detalhe", id=id))

    if candidato_bloqueado_para_vaga(current_user.id, vaga.id):
        mensagem = "Você não pode se candidatar novamente a esta vaga."
        if quer_json():
            return jsonify({"ok": False, "message": mensagem}), 403
        flash(mensagem, "warning")
        return redirect(url_for("vagas.detalhe", id=id))

    DescarteVaga.query.filter_by(candidato_id=current_user.id, vaga_id=vaga.id).delete()
    interesse = Interesse(candidato_id=current_user.id, vaga_id=vaga.id)
    db.session.add(interesse)
    try:
        db.session.flush()
        foi_match = verificar_e_criar_match(
            current_user.id, vaga.contratante_id, vaga.id
        )
        db.session.commit()
        if quer_json():
            return jsonify(
                {"ok": True, "action": "like", "vaga_id": vaga.id, "match": foi_match}
            )
        if foi_match:
            flash(
                "É um match! O contratante também tem interesse no seu perfil.",
                "success",
            )
        else:
            flash("Interesse registrado com sucesso.", "success")
    except IntegrityError:
        db.session.rollback()
        if quer_json():
            return jsonify(
                {"ok": True, "action": "like", "vaga_id": vaga.id, "match": False}
            )
        flash("Você já demonstrou interesse nesta vaga.", "warning")
    return redirect(url_for("vagas.listagem"))


@bp_vagas.route("/<int:id>/descartar", methods=["POST"])
@login_required
def descartar(id):
    exigir_candidato()
    if perfil_candidato_obrigatorio() is None:
        return redirect(url_for("candidato.perfil"))

    vaga = db.get_or_404(Vaga, id)
    Interesse.query.filter_by(candidato_id=current_user.id, vaga_id=vaga.id).delete()
    descarte = DescarteVaga(candidato_id=current_user.id, vaga_id=vaga.id)
    db.session.add(descarte)
    try:
        db.session.commit()
        if quer_json():
            return jsonify({"ok": True, "action": "skip", "vaga_id": vaga.id})
        flash("Vaga descartada.", "info")
    except IntegrityError:
        db.session.rollback()
        if quer_json():
            return jsonify({"ok": True, "action": "skip", "vaga_id": vaga.id})
        flash("Esta vaga já foi descartada.", "warning")
    return redirect(url_for("vagas.listagem"))


@bp_vagas.route("/<int:id>/remover_interesse", methods=["POST"])
@login_required
def remover_interesse(id):
    exigir_candidato()
    interesse = Interesse.query.filter_by(
        candidato_id=current_user.id, vaga_id=id
    ).first_or_404()
    db.session.delete(interesse)
    db.session.commit()
    flash("Interesse removido com sucesso.", "info")
    return redirect(url_for("candidato.minhas_vagas"))
