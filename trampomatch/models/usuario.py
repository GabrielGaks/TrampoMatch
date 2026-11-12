from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from flask_login import UserMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from werkzeug.security import check_password_hash, generate_password_hash

from trampomatch.extensions import db

if TYPE_CHECKING:
    from trampomatch.models.descarte_contratante import DescarteContratante
    from trampomatch.models.descarte_vaga import DescarteVaga
    from trampomatch.models.interesse import Interesse
    from trampomatch.models.interesse_contratante import InteresseContratante
    from trampomatch.models.match import Match
    from trampomatch.models.vaga import Vaga


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(db.String(100), nullable=False)
    email: Mapped[str] = mapped_column(
        db.String(150), unique=True, index=True, nullable=False
    )
    senha_hash: Mapped[str | None] = mapped_column(db.String(256), nullable=True)
    google_id: Mapped[str | None] = mapped_column(
        db.String(200), unique=True, nullable=True
    )
    tipo_perfil: Mapped[str] = mapped_column(db.String(20), nullable=False)
    ativo: Mapped[bool] = mapped_column(db.Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(db.DateTime, server_default=func.now())
    ultimo_acesso_dashboard: Mapped[datetime | None] = mapped_column(db.DateTime, nullable=True)

    perfil_candidato: Mapped["PerfilCandidato | None"] = relationship(
        back_populates="usuario", uselist=False, cascade="all, delete-orphan"
    )
    perfil_contratante: Mapped["PerfilContratante | None"] = relationship(
        back_populates="usuario", uselist=False, cascade="all, delete-orphan"
    )
    vagas_cadastradas: Mapped[list["Vaga"]] = relationship(
        back_populates="contratante", cascade="all, delete-orphan"
    )
    interesses: Mapped[list["Interesse"]] = relationship(
        back_populates="candidato", cascade="all, delete-orphan"
    )
    descartes_vagas: Mapped[list["DescarteVaga"]] = relationship(
        back_populates="candidato", cascade="all, delete-orphan"
    )
    interesses_em_candidatos: Mapped[list["InteresseContratante"]] = relationship(
        foreign_keys="InteresseContratante.contratante_id",
        back_populates="contratante",
        cascade="all, delete-orphan",
    )
    interesses_recebidos: Mapped[list["InteresseContratante"]] = relationship(
        foreign_keys="InteresseContratante.candidato_id",
        back_populates="candidato",
        cascade="all, delete-orphan",
    )
    descartes_em_candidatos: Mapped[list["DescarteContratante"]] = relationship(
        foreign_keys="DescarteContratante.contratante_id",
        back_populates="contratante",
        cascade="all, delete-orphan",
    )
    descartes_recebidos: Mapped[list["DescarteContratante"]] = relationship(
        foreign_keys="DescarteContratante.candidato_id",
        back_populates="candidato",
        cascade="all, delete-orphan",
    )
    matches_como_candidato: Mapped[list["Match"]] = relationship(
        foreign_keys="Match.candidato_id",
        back_populates="candidato",
        cascade="all, delete-orphan",
    )
    matches_como_contratante: Mapped[list["Match"]] = relationship(
        foreign_keys="Match.contratante_id",
        back_populates="contratante",
        cascade="all, delete-orphan",
    )

    def set_senha(self, senha: str) -> None:
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha: str) -> bool:
        if not self.senha_hash:
            return False
        return check_password_hash(self.senha_hash, senha)

    @property
    def eh_candidato(self) -> bool:
        return self.tipo_perfil == "candidato"

    @property
    def eh_contratante(self) -> bool:
        return self.tipo_perfil == "contratante"


class PerfilCandidato(db.Model):
    __tablename__ = "perfis_candidatos"

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        db.Integer, db.ForeignKey("usuarios.id"), unique=True, nullable=False
    )
    regiao: Mapped[str] = mapped_column(db.String(100), nullable=False)
    tipo_trabalho: Mapped[str] = mapped_column(db.String(50), nullable=False)
    disponibilidade: Mapped[str] = mapped_column(db.String(100), nullable=False)
    habilidades: Mapped[str] = mapped_column(db.Text, nullable=False)
    experiencia_resumida: Mapped[str | None] = mapped_column(db.Text)
    nivel_experiencia: Mapped[int] = mapped_column(db.Integer, nullable=False)
    curriculo_arquivo: Mapped[str | None] = mapped_column(db.String(255))
    curriculo_nome_original: Mapped[str | None] = mapped_column(db.String(255))
    curriculo_enviado_em: Mapped[datetime | None] = mapped_column(db.DateTime)
    categoria: Mapped[str | None] = mapped_column(db.String(60), nullable=True)

    usuario: Mapped[Usuario] = relationship(back_populates="perfil_candidato")

    def habilidades_lista(self) -> list[str]:
        return [h.strip().lower() for h in self.habilidades.split(",") if h.strip()]

    @property
    def nivel_experiencia_rotulo(self) -> str:
        from trampomatch.services.compatibilidade import categoria_experiencia

        return categoria_experiencia(self.nivel_experiencia)["rotulo"]


class PerfilContratante(db.Model):
    __tablename__ = "perfis_contratantes"

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        db.Integer, db.ForeignKey("usuarios.id"), unique=True, nullable=False
    )
    nome_empresa: Mapped[str | None] = mapped_column(db.String(150))
    logo_empresa: Mapped[str | None] = mapped_column(db.String(255))
    regiao: Mapped[str] = mapped_column(db.String(100), nullable=False)
    tipo_contratante: Mapped[str | None] = mapped_column(db.String(30))
    quantidade_funcionarios: Mapped[str | None] = mapped_column(db.String(20))
    areas_atuacao: Mapped[str | None] = mapped_column(db.Text)
    site: Mapped[str | None] = mapped_column(db.String(200))
    descricao: Mapped[str | None] = mapped_column(db.Text)

    usuario: Mapped[Usuario] = relationship(back_populates="perfil_contratante")

    @property
    def percentual_completo(self) -> int:
        campos = [
            self.nome_empresa,
            self.logo_empresa,
            self.regiao,
            self.tipo_contratante,
            self.quantidade_funcionarios,
            self.areas_atuacao,
            self.site,
            self.descricao,
        ]
        preenchidos = sum(1 for campo in campos if campo)
        return round((preenchidos / len(campos)) * 100)

    def areas_atuacao_lista(self) -> list[str]:
        return [
            area.strip()
            for area in (self.areas_atuacao or "").split(",")
            if area.strip()
        ]
