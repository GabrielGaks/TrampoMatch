from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from trampomatch.extensions import db

if TYPE_CHECKING:
    from trampomatch.models.usuario import Usuario
    from trampomatch.models.vaga import Vaga


class RecusaCandidaturaVaga(db.Model):
    __tablename__ = "recusas_candidatura_vaga"
    __table_args__ = (db.UniqueConstraint("candidato_id", "vaga_id"),)

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    candidato_id: Mapped[int] = mapped_column(
        db.Integer, db.ForeignKey("usuarios.id"), nullable=False
    )
    vaga_id: Mapped[int] = mapped_column(
        db.Integer, db.ForeignKey("vagas.id"), nullable=False
    )
    contratante_id: Mapped[int] = mapped_column(
        db.Integer, db.ForeignKey("usuarios.id"), nullable=False
    )
    criado_em: Mapped[datetime] = mapped_column(db.DateTime, server_default=func.now())

    candidato: Mapped["Usuario"] = relationship(foreign_keys=[candidato_id])
    contratante: Mapped["Usuario"] = relationship(foreign_keys=[contratante_id])
    vaga: Mapped["Vaga"] = relationship(foreign_keys=[vaga_id])
