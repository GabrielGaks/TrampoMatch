import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template
from sqlalchemy import inspect, text
from trampomatch.config import config_by_name
from trampomatch.extensions import csrf, db, login_manager, oauth
from trampomatch.views import init_app as init_views


def _read_env_value(key: str) -> str:
    env_file = Path(__file__).parent.parent / ".env.dev"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip()
    return os.environ.get(key, "")


def create_app(config_name="development"):
    _env = Path(__file__).parent.parent / ".env.dev"
    if _env.exists():
        load_dotenv(_env, override=True)

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])
    if config_name == "production" and not os.environ.get("SECRET_KEY"):
        raise RuntimeError("Defina SECRET_KEY para rodar em produção.")

    app.config["GOOGLE_CLIENT_ID"] = _read_env_value("GOOGLE_CLIENT_ID")
    app.config["GOOGLE_CLIENT_SECRET"] = _read_env_value("GOOGLE_CLIENT_SECRET")

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    oauth.init_app(app)

    oauth.register(
        name="google",
        client_id=app.config["GOOGLE_CLIENT_ID"],
        client_secret=app.config["GOOGLE_CLIENT_SECRET"],
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    init_views(app)

    from trampomatch import models  # noqa: F401

    register_error_handlers(app)

    with app.app_context():
        db.create_all()
        ensure_sqlite_schema()
        _seed_habilidades()

    return app


def ensure_sqlite_schema():
    if db.engine.dialect.name != "sqlite":
        return

    inspector = inspect(db.engine)
    tabelas = inspector.get_table_names()

    if "vagas" in tabelas:
        colunas_vagas = {c["name"] for c in inspector.get_columns("vagas")}
        if "disponibilidade" not in colunas_vagas:
            db.session.execute(
                text(
                    "ALTER TABLE vagas ADD COLUMN disponibilidade VARCHAR(120) NOT NULL DEFAULT ''"
                )
            )
            db.session.commit()
        if "categoria" not in colunas_vagas:
            db.session.execute(
                text("ALTER TABLE vagas ADD COLUMN categoria VARCHAR(60)")
            )
            db.session.commit()

    if "usuarios" in tabelas:
        colunas_usuarios = {c["name"] for c in inspector.get_columns("usuarios")}
        if "google_id" not in colunas_usuarios:
            db.session.execute(
                text("ALTER TABLE usuarios ADD COLUMN google_id VARCHAR(200)")
            )
            db.session.commit()
        if "ultimo_acesso_dashboard" not in colunas_usuarios:
            db.session.execute(
                text("ALTER TABLE usuarios ADD COLUMN ultimo_acesso_dashboard DATETIME")
            )
            db.session.commit()

    if "perfis_contratantes" in tabelas:
        colunas_perfil = {
            c["name"] for c in inspector.get_columns("perfis_contratantes")
        }
        novas_colunas = {
            "nome_empresa": "VARCHAR(150)",
            "logo_empresa": "VARCHAR(255)",
            "tipo_contratante": "VARCHAR(30)",
            "quantidade_funcionarios": "VARCHAR(20)",
            "areas_atuacao": "TEXT",
            "site": "VARCHAR(200)",
        }
        for nome, tipo in novas_colunas.items():
            if nome not in colunas_perfil:
                db.session.execute(
                    text(f"ALTER TABLE perfis_contratantes ADD COLUMN {nome} {tipo}")
                )
        db.session.commit()

    if "perfis_candidatos" in tabelas:
        colunas_perfil_candidato = {
            c["name"] for c in inspector.get_columns("perfis_candidatos")
        }
        novas_colunas_candidato = {
            "curriculo_arquivo": "VARCHAR(255)",
            "curriculo_nome_original": "VARCHAR(255)",
            "curriculo_enviado_em": "DATETIME",
            "categoria": "VARCHAR(60)",
        }
        for nome, tipo in novas_colunas_candidato.items():
            if nome not in colunas_perfil_candidato:
                db.session.execute(
                    text(f"ALTER TABLE perfis_candidatos ADD COLUMN {nome} {tipo}")
                )
        db.session.commit()

    if "interesses_contratantes" in tabelas:
        cols = {c["name"] for c in inspector.get_columns("interesses_contratantes")}
        if "vaga_id" not in cols:
            db.session.execute(
                text(
                    "ALTER TABLE interesses_contratantes "
                    "ADD COLUMN vaga_id INTEGER REFERENCES vagas(id)"
                )
            )
            db.session.commit()

    if "matches" in tabelas:
        cols = {c["name"] for c in inspector.get_columns("matches")}
        if "vaga_id" not in cols:
            db.session.execute(
                text(
                    "ALTER TABLE matches ADD COLUMN vaga_id INTEGER REFERENCES vagas(id)"
                )
            )
        novas_colunas_matches = {
            "mensagem_contratante": "TEXT",
            "contato_email": "VARCHAR(150)",
            "contato_telefone": "VARCHAR(30)",
            "mensagem_enviada_em": "DATETIME",
        }
        for nome, tipo in novas_colunas_matches.items():
            if nome not in cols:
                db.session.execute(
                    text(f"ALTER TABLE matches ADD COLUMN {nome} {tipo}")
                )
        db.session.commit()


def _seed_habilidades():
    from trampomatch.forms.candidato import HABILIDADES_PREDEFINIDAS
    from trampomatch.models.habilidade import Habilidade

    if Habilidade.query.count() > 0:
        return
    for nome in HABILIDADES_PREDEFINIDAS:
        db.session.add(Habilidade(nome=nome))
    db.session.commit()


def register_error_handlers(app):
    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500
