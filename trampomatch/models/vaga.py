from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from trampomatch.extensions import db

if TYPE_CHECKING:
    from trampomatch.models.descarte_vaga import DescarteVaga
    from trampomatch.models.interesse import Interesse
    from trampomatch.models.usuario import Usuario


COMPLEXIDADE_CATEGORIAS = (
    {
        "slug": "simples",
        "rotulo": "Simples",
        "descricao": "Atividades rotineiras, com baixa autonomia exigida.",
        "valor": 20,
        "min": 1,
        "max": 30,
        "ordem": 1,
    },
    {
        "slug": "moderada",
        "rotulo": "Moderada",
        "descricao": "Exige alguma experiencia previa e organizacao.",
        "valor": 45,
        "min": 31,
        "max": 55,
        "ordem": 2,
    },
    {
        "slug": "alta",
        "rotulo": "Alta",
        "descricao": "Exige experiencia consistente e tomada de decisao.",
        "valor": 70,
        "min": 56,
        "max": 80,
        "ordem": 3,
    },
    {
        "slug": "especializada",
        "rotulo": "Especializada",
        "descricao": "Exige dominio tecnico, autonomia e responsabilidade elevada.",
        "valor": 90,
        "min": 81,
        "max": 100,
        "ordem": 4,
    },
)


def categoria_complexidade(valor) -> dict:
    try:
        numero = int(valor or 0)
    except (TypeError, ValueError):
        numero = 0

    for categoria in COMPLEXIDADE_CATEGORIAS:
        if categoria["min"] <= numero <= categoria["max"]:
            return categoria
    return COMPLEXIDADE_CATEGORIAS[0]


class Vaga(db.Model):
    __tablename__ = "vagas"

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    contratante_id: Mapped[int] = mapped_column(
        db.Integer, db.ForeignKey("usuarios.id"), nullable=False
    )
    titulo: Mapped[str] = mapped_column(db.String(150), nullable=False)
    descricao: Mapped[str] = mapped_column(db.Text, nullable=False)
    regiao: Mapped[str] = mapped_column(db.String(100), nullable=False)
    tipo_vaga: Mapped[str] = mapped_column(db.String(50), nullable=False)
    disponibilidade: Mapped[str] = mapped_column(
        db.String(120), nullable=False, default=""
    )
    valor_min: Mapped[float | None] = mapped_column(db.Float)
    valor_max: Mapped[float | None] = mapped_column(db.Float)
    data_inicio: Mapped[date | None] = mapped_column(db.Date)
    data_fim: Mapped[date | None] = mapped_column(db.Date)
    habilidades_desejadas: Mapped[str] = mapped_column(db.Text, nullable=False)
    complexidade: Mapped[int] = mapped_column(db.Integer, nullable=False)
    categoria: Mapped[str | None] = mapped_column(db.String(60), nullable=True)
    status: Mapped[str] = mapped_column(db.String(20), default="aberta")
    criado_em: Mapped[datetime] = mapped_column(db.DateTime, server_default=func.now())

    contratante: Mapped["Usuario"] = relationship(back_populates="vagas_cadastradas")
    interesses: Mapped[list["Interesse"]] = relationship(
        back_populates="vaga", cascade="all, delete-orphan"
    )
    descartes: Mapped[list["DescarteVaga"]] = relationship(
        back_populates="vaga", cascade="all, delete-orphan"
    )

    def habilidades_lista(self) -> list[str]:
        return [
            h.strip().lower()
            for h in self.habilidades_desejadas.split(",")
            if h.strip()
        ]

    def total_interessados(self) -> int:
        from trampomatch.services.candidatura import contar_interessados_pendentes

        return contar_interessados_pendentes(self.id, self.contratante_id)

    @property
    def complexidade_categoria(self) -> str:
        return categoria_complexidade(self.complexidade)["slug"]

    @property
    def complexidade_rotulo(self) -> str:
        return categoria_complexidade(self.complexidade)["rotulo"]

    @property
    def complexidade_descricao(self) -> str:
        return categoria_complexidade(self.complexidade)["descricao"]

    @property
    def complexidade_percentual(self) -> int:
        return categoria_complexidade(self.complexidade)["valor"]
