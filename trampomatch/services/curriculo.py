from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

PASTA_CURRICULOS = Path("uploads") / "curriculos"


def pasta_curriculos() -> Path:
    pasta = Path(current_app.instance_path) / PASTA_CURRICULOS
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def caminho_curriculo(nome_arquivo: str | None) -> Path | None:
    if not nome_arquivo:
        return None

    pasta = pasta_curriculos().resolve()
    caminho = (pasta / nome_arquivo).resolve()
    if pasta not in caminho.parents and caminho != pasta:
        return None
    return caminho


def remover_arquivo_curriculo(nome_arquivo: str | None) -> None:
    caminho = caminho_curriculo(nome_arquivo)
    if caminho and caminho.exists():
        caminho.unlink()


def limpar_curriculo(perfil) -> None:
    remover_arquivo_curriculo(perfil.curriculo_arquivo)
    perfil.curriculo_arquivo = None
    perfil.curriculo_nome_original = None
    perfil.curriculo_enviado_em = None


def salvar_curriculo(perfil, arquivo: FileStorage) -> None:
    nome_original = secure_filename(arquivo.filename or "")
    extensao = Path(nome_original).suffix.lower()
    nome_interno = f"{uuid4().hex}{extensao}"
    destino = pasta_curriculos() / nome_interno

    remover_arquivo_curriculo(perfil.curriculo_arquivo)
    arquivo.save(destino)

    perfil.curriculo_arquivo = nome_interno
    perfil.curriculo_nome_original = nome_original
    perfil.curriculo_enviado_em = datetime.now(UTC).replace(tzinfo=None)
