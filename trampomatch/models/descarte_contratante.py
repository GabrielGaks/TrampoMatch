from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from trampomatch.extensions import db

if TYPE_CHECKING:
    from trampomatch.models.usuario import Usuario


class DescarteContratante(db.Model):
    __tablename__ = "descartes_contratantes"
    __table_args__ = (db.UniqueConstraint("contratante_id", "candidato_id"),)

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    contratante_id: Mapped[int] = mapped_column(
        db.Integer, db.ForeignKey("usuarios.id"), nullable=False
    )
    candidato_id: Mapped[int] = mapped_column(
        db.Integer, db.ForeignKey("usuarios.id"), nullable=False
    )
    criado_em: Mapped[datetime] = mapped_column(db.DateTime, server_default=func.now())

    contratante: Mapped["Usuario"] = relationship(
        foreign_keys=[contratante_id], back_populates="descartes_em_candidatos"
    )
    candidato: Mapped["Usuario"] = relationship(
        foreign_keys=[candidato_id], back_populates="descartes_recebidos"
    )
