from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from trampomatch.extensions import db

if TYPE_CHECKING:
    from trampomatch.models.usuario import Usuario
    from trampomatch.models.vaga import Vaga


class Match(db.Model):
    __tablename__ = "matches"
    __table_args__ = (db.UniqueConstraint("candidato_id", "contratante_id", "vaga_id"),)

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    candidato_id: Mapped[int] = mapped_column(
        db.Integer, db.ForeignKey("usuarios.id"), nullable=False
    )
    contratante_id: Mapped[int] = mapped_column(
        db.Integer, db.ForeignKey("usuarios.id"), nullable=False
    )
    vaga_id: Mapped[int | None] = mapped_column(
        db.Integer, db.ForeignKey("vagas.id"), nullable=True
    )
    criado_em: Mapped[datetime] = mapped_column(db.DateTime, server_default=func.now())
    status: Mapped[str] = mapped_column(db.String(20), default="ativo")
    mensagem_contratante: Mapped[str | None] = mapped_column(db.Text, nullable=True)
    contato_email: Mapped[str | None] = mapped_column(db.String(150), nullable=True)
    contato_telefone: Mapped[str | None] = mapped_column(db.String(30), nullable=True)
    mensagem_enviada_em: Mapped[datetime | None] = mapped_column(
        db.DateTime, nullable=True
    )

    candidato: Mapped["Usuario"] = relationship(
        foreign_keys=[candidato_id], back_populates="matches_como_candidato"
    )
    contratante: Mapped["Usuario"] = relationship(
        foreign_keys=[contratante_id], back_populates="matches_como_contratante"
    )
    vaga: Mapped["Vaga | None"] = relationship(foreign_keys=[vaga_id])
