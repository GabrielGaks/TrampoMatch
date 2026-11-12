import secrets
from pathlib import Path
from uuid import uuid4

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_login import current_user, login_user, logout_user
from werkzeug.utils import secure_filename

from trampomatch.extensions import db, oauth
from trampomatch.forms import (
    CadastroForm,
    GoogleCandidatoOnboardingForm,
    GoogleContratanteOnboardingForm,
    LoginForm,
)
from trampomatch.forms.auth import AREAS_ATUACAO_PREDEFINIDAS, normalizar_areas_atuacao
from trampomatch.forms.candidato import (
    COORDENADAS_REGIOES,
    HABILIDADES_PREDEFINIDAS,
    REGIOES_GRANDE_VITORIA,
)
from trampomatch.models import PerfilCandidato, PerfilContratante, Usuario
from trampomatch.services.curriculo import salvar_curriculo

bp_auth = Blueprint("auth", __name__, url_prefix="/auth")


def destino_usuario(usuario):
    if usuario.eh_candidato:
        return "candidato.dashboard" if usuario.perfil_candidato else "candidato.perfil"
    return (
        "contratante.dashboard" if usuario.perfil_contratante else "contratante.perfil"
    )


def _salvar_logo_empresa(arquivo):
    if not arquivo or not getattr(arquivo, "filename", ""):
        return None

    pasta_upload = Path(current_app.instance_path) / "uploads" / "logos_empresas"
    pasta_upload.mkdir(parents=True, exist_ok=True)

    nome_seguro = secure_filename(arquivo.filename)
    nome_arquivo = f"{uuid4().hex}_{nome_seguro}"
    caminho_absoluto = pasta_upload / nome_arquivo
    arquivo.save(caminho_absoluto)
    return f"uploads/logos_empresas/{nome_arquivo}"


def caminho_logo_empresa(nome_relativo):
    if not nome_relativo:
        return None

    caminho = (Path(current_app.instance_path) / nome_relativo).resolve()
    pasta_upload = (Path(current_app.instance_path) / "uploads" / "logos_empresas").resolve()
    try:
        caminho.relative_to(pasta_upload)
    except ValueError:
        return None
    return caminho if caminho.is_file() else None


@bp_auth.route("/logos/empresa/<path:nome_arquivo>")
def logo_empresa(nome_arquivo):
    caminho = caminho_logo_empresa(f"uploads/logos_empresas/{nome_arquivo}")
    if not caminho:
        abort(404)
    return send_file(caminho)


def _criar_usuario_google(dados, tipo_perfil):
    usuario = Usuario(
        nome=dados["nome"],
        email=dados["email"],
        google_id=dados["google_id"],
        tipo_perfil=tipo_perfil,
    )
    usuario.set_senha(secrets.token_hex(32))
    db.session.add(usuario)
    db.session.flush()
    return usuario


def _login_usuario_google_existente(dados):
    usuario = Usuario.query.filter_by(google_id=dados["google_id"]).first()
    if not usuario:
        usuario = Usuario.query.filter_by(email=dados["email"]).first()
        if usuario:
            usuario.google_id = dados["google_id"]
            db.session.commit()

    if not usuario:
        return None

    if not usuario.ativo:
        flash("Conta desativada. Entre em contato com o suporte.", "danger")
        return redirect(url_for("auth.login"))

    session.pop("google_pending", None)
    login_user(usuario)
    session["show_novidades"] = True
    return redirect(url_for(destino_usuario(usuario)))


@bp_auth.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if current_user.is_authenticated:
        return redirect(url_for(destino_usuario(current_user)))

    form = CadastroForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if Usuario.query.filter_by(email=email).first():
            flash("Este e-mail já está cadastrado.", "danger")
            return render_template("auth/cadastro.html", form=form)

        usuario = Usuario(
            nome=form.nome.data.strip(),
            email=email,
            tipo_perfil=form.tipo_perfil.data,
        )
        usuario.set_senha(form.senha.data)
        db.session.add(usuario)
        db.session.commit()
        flash("Cadastro realizado com sucesso. Faça login para continuar.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/cadastro.html", form=form)


@bp_auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for(destino_usuario(current_user)))

    form = LoginForm()
    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(email=form.email.data.strip().lower()).first()
        if usuario and usuario.verificar_senha(form.senha.data) and usuario.ativo:
            login_user(usuario)
            session["show_novidades"] = True
            session["novidades_ts"] = session.get("ultimo_dashboard")
            proxima = request.args.get("next")
            return redirect(proxima or url_for(destino_usuario(usuario)))
        flash("E-mail ou senha inválidos.", "danger")

    return render_template("auth/login.html", form=form)


@bp_auth.route("/logout")
def logout():
    logout_user()
    flash("Sessão encerrada com sucesso.", "info")
    return redirect(url_for("main.index"))


@bp_auth.route("/google/login")
def google_login():
    redirect_uri = url_for("auth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@bp_auth.route("/google/callback")
def google_callback():
    token = oauth.google.authorize_access_token()
    info = token.get("userinfo") or oauth.google.userinfo()

    google_id = info["sub"]
    email = info["email"].strip().lower()
    nome = info.get("name", email.split("@")[0])

    usuario = Usuario.query.filter_by(google_id=google_id).first()

    if not usuario:
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario:
            usuario.google_id = google_id
            db.session.commit()

    if usuario:
        if not usuario.ativo:
            flash("Conta desativada. Entre em contato com o suporte.", "danger")
            return redirect(url_for("auth.login"))
        login_user(usuario)
        session["show_novidades"] = True
        session["novidades_ts"] = session.get("ultimo_dashboard")
        return redirect(url_for(destino_usuario(usuario)))

    session["google_pending"] = {"google_id": google_id, "email": email, "nome": nome}
    return redirect(url_for("auth.google_escolher_perfil"))


@bp_auth.route("/google/escolher-perfil", methods=["GET", "POST"])
def google_escolher_perfil():
    dados = session.get("google_pending")
    if not dados:
        return redirect(url_for("auth.login"))

    redirecionamento = _login_usuario_google_existente(dados)
    if redirecionamento:
        return redirecionamento

    def _render(erro=None):
        if erro:
            flash(erro, "danger")
        return render_template("auth/escolher_perfil_google.html", nome=dados["nome"])

    if request.method == "POST":
        tipo_perfil = request.form.get("tipo_perfil")

        if tipo_perfil not in ("candidato", "contratante"):
            return _render("Escolha um tipo de perfil válido.")

        dados["tipo_perfil"] = tipo_perfil
        session["google_pending"] = dados
        return redirect(url_for("auth.google_completar_perfil"))

    return _render()


@bp_auth.route("/google/completar-perfil", methods=["GET", "POST"])
def google_completar_perfil():
    dados = session.get("google_pending")
    if not dados:
        return redirect(url_for("auth.login"))

    redirecionamento = _login_usuario_google_existente(dados)
    if redirecionamento:
        return redirecionamento

    tipo_perfil = dados.get("tipo_perfil")
    if tipo_perfil not in ("candidato", "contratante"):
        return redirect(url_for("auth.google_escolher_perfil"))

    form = (
        GoogleCandidatoOnboardingForm()
        if tipo_perfil == "candidato"
        else GoogleContratanteOnboardingForm()
    )

    if form.validate_on_submit():
        usuario = _criar_usuario_google(dados, tipo_perfil)

        if tipo_perfil == "candidato":
            perfil_candidato = PerfilCandidato(
                usuario_id=usuario.id,
                regiao=form.regiao.data.strip(),
                tipo_trabalho=form.tipo_trabalho.data,
                disponibilidade=form.disponibilidade.data,
                habilidades=form.habilidades.data.strip(),
                experiencia_resumida=(form.experiencia_resumida.data or "").strip(),
                nivel_experiencia=form.nivel_experiencia.data,
            )
            if form.curriculo.data and form.curriculo.data.filename:
                salvar_curriculo(perfil_candidato, form.curriculo.data)
            db.session.add(
                perfil_candidato
            )
        else:
            db.session.add(
                PerfilContratante(
                    usuario_id=usuario.id,
                    nome_empresa=form.nome_empresa.data.strip(),
                    logo_empresa=_salvar_logo_empresa(form.logo_empresa.data),
                    regiao=form.regiao.data.strip(),
                    tipo_contratante=form.tipo_contratante.data,
                    quantidade_funcionarios=form.quantidade_funcionarios.data,
                    areas_atuacao=normalizar_areas_atuacao(form.areas_atuacao.data),
                    site=(form.site.data or "").strip() or None,
                    descricao=form.descricao.data.strip(),
                )
            )

        db.session.commit()
        session.pop("google_pending", None)
        login_user(usuario)
        session["show_novidades"] = True
        session["novidades_ts"] = session.get("ultimo_dashboard")
        flash(
            f"Bem-vindo, {usuario.nome}! Seu perfil foi criado com sucesso.", "success"
        )
        return redirect(url_for(destino_usuario(usuario)))

    return render_template(
        "auth/google_onboarding.html",
        form=form,
        perfil=None,
        nome=dados["nome"],
        primeiro_nome=dados["nome"].split()[0],
        tipo_perfil=tipo_perfil,
        regioes=REGIOES_GRANDE_VITORIA,
        coordenadas_regioes=COORDENADAS_REGIOES,
        habilidades_predefinidas=HABILIDADES_PREDEFINIDAS,
        areas_atuacao_predefinidas=AREAS_ATUACAO_PREDEFINIDAS,
        percentual_base=40,
    )
