from invoke import task
import sys


@task
def install(c):
    """Instala o projeto em modo editável."""
    c.run('pip install -e ".[dev,test]"', echo=True)


@task
def run(c):
    """Executa a aplicação Flask em modo de desenvolvimento."""
    c.run(f'"{sys.executable}" -m dotenv -f .env.dev run -- "{sys.executable}" -m flask --app app run --debug --host localhost', pty=False)


@task
def test(c):
    """Executa os testes automatizados com cobertura."""
    c.run(
        f'"{sys.executable}" -m pytest -v --cov=trampomatch --cov-report=term-missing',
        echo=True,
    )


@task
def lint(c):
    """Verifica o estilo do código com flake8."""
    c.run(f'"{sys.executable}" -m flake8 trampomatch/ tests/', echo=True)


@task
def format(c):
    """Formata o código com black."""
    c.run(f'"{sys.executable}" -m black trampomatch/ tests/', echo=True)
