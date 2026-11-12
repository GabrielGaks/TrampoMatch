from __future__ import annotations

from typing import TYPE_CHECKING

from trampomatch.extensions import db
from trampomatch.models.descarte_contratante import DescarteContratante
from trampomatch.models.descarte_vaga import DescarteVaga
from trampomatch.models.interesse import Interesse
from trampomatch.models.interesse_contratante import InteresseContratante
from trampomatch.models.recusa_candidatura_vaga import RecusaCandidaturaVaga
from trampomatch.models.vaga import Vaga

if TYPE_CHECKING:
    from trampomatch.models.usuario import PerfilCandidato


def candidato_bloqueado_para_vaga(candidato_id: int, vaga_id: int) -> bool:
    return (
        RecusaCandidaturaVaga.query.filter_by(
            candidato_id=candidato_id, vaga_id=vaga_id
        ).first()
        is not None
    )


def query_vagas_abertas_para_candidato(candidato_id: int, perfil: PerfilCandidato | None):
    """Vagas abertas da categoria do perfil, excluindo interesses, descartes e recusas."""
    interesses_ids = db.session.query(Interesse.vaga_id).filter_by(
        candidato_id=candidato_id
    )
    descartes_ids = db.session.query(DescarteVaga.vaga_id).filter_by(
        candidato_id=candidato_id
    )
    recusas_ids = db.session.query(RecusaCandidaturaVaga.vaga_id).filter_by(
        candidato_id=candidato_id
    )
    query = (
        Vaga.query.filter_by(status="aberta")
        .filter(
            ~Vaga.id.in_(interesses_ids),
            ~Vaga.id.in_(descartes_ids),
            ~Vaga.id.in_(recusas_ids),
        )
        .order_by(Vaga.criado_em.desc())
    )
    if perfil and perfil.categoria:
        query = query.filter(Vaga.categoria == perfil.categoria)
    return query


def vagas_abertas_para_candidato(candidato_id: int, perfil: PerfilCandidato | None) -> list[Vaga]:
    return query_vagas_abertas_para_candidato(candidato_id, perfil).all()


def query_interessados_pendentes(vaga_id: int, contratante_id: int):
    """Candidatos que demonstraram interesse e ainda aguardam avaliação."""
    interesses_respondidos = db.session.query(
        InteresseContratante.candidato_id
    ).filter_by(contratante_id=contratante_id, vaga_id=vaga_id)
    descartes_ids = db.session.query(DescarteContratante.candidato_id).filter_by(
        contratante_id=contratante_id
    )
    recusas_ids = db.session.query(RecusaCandidaturaVaga.candidato_id).filter_by(
        vaga_id=vaga_id
    )
    return Interesse.query.filter_by(vaga_id=vaga_id).filter(
        ~Interesse.candidato_id.in_(interesses_respondidos),
        ~Interesse.candidato_id.in_(descartes_ids),
        ~Interesse.candidato_id.in_(recusas_ids),
    )


def contar_interessados_pendentes(vaga_id: int, contratante_id: int) -> int:
    return query_interessados_pendentes(vaga_id, contratante_id).count()
