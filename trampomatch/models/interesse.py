from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from trampomatch.extensions import db

if TYPE_CHECKING:
    from trampomatch.models.usuario import Usuario
    from trampomatch.models.vaga import Vaga


class Interesse(db.Model):
    __tablename__ = "interesses"
    __table_args__ = (db.UniqueConstraint("candidato_id", "vaga_id"),)

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    candidato_id: Mapped[int] = mapped_column(
        db.Integer, db.ForeignKey("usuarios.id"), nullable=False
    )
    vaga_id: Mapped[int] = mapped_column(
        db.Integer, db.ForeignKey("vagas.id"), nullable=False
    )
    criado_em: Mapped[datetime] = mapped_column(db.DateTime, server_default=func.now())

    candidato: Mapped["Usuario"] = relationship(back_populates="interesses")
    vaga: Mapped["Vaga"] = relationship(back_populates="interesses")
