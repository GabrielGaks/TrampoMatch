from __future__ import annotations


def verificar_e_criar_match(
    candidato_id: int, contratante_id: int, vaga_id: int | None = None
) -> bool:
    from trampomatch.extensions import db
    from trampomatch.models.interesse import Interesse
    from trampomatch.models.interesse_contratante import InteresseContratante
    from trampomatch.models.match import Match
    from trampomatch.models.vaga import Vaga

    if vaga_id is not None:
        # Novo fluxo: match escopado por vaga
        candidato_interessado = Interesse.query.filter_by(
            candidato_id=candidato_id,
            vaga_id=vaga_id,
        ).first()
        contratante_interessado = InteresseContratante.query.filter_by(
            contratante_id=contratante_id,
            candidato_id=candidato_id,
            vaga_id=vaga_id,
        ).first()

        if not (candidato_interessado and contratante_interessado):
            return False

        ja_existe = Match.query.filter_by(
            candidato_id=candidato_id,
            contratante_id=contratante_id,
            vaga_id=vaga_id,
        ).first()
        if ja_existe:
            return False

        db.session.add(
            Match(
                candidato_id=candidato_id,
                contratante_id=contratante_id,
                vaga_id=vaga_id,
            )
        )
        return True

    # Fallback legado: sem vaga_id (compatibilidade com registros antigos)
    candidato_interessado = (
        Interesse.query.join(Vaga, Interesse.vaga_id == Vaga.id)
        .filter(
            Interesse.candidato_id == candidato_id,
            Vaga.contratante_id == contratante_id,
        )
        .first()
    )
    contratante_interessado = InteresseContratante.query.filter_by(
        contratante_id=contratante_id,
        candidato_id=candidato_id,
    ).first()

    if not (candidato_interessado and contratante_interessado):
        return False

    ja_existe = Match.query.filter_by(
        candidato_id=candidato_id,
        contratante_id=contratante_id,
        vaga_id=None,
    ).first()
    if ja_existe:
        return False

    db.session.add(Match(candidato_id=candidato_id, contratante_id=contratante_id))
    return True
