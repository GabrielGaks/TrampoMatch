from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileSize
from wtforms import (
    EmailField,
    HiddenField,
    PasswordField,
    RadioField,
    SelectField,
    StringField,
)
from wtforms import SubmitField, TextAreaField
from wtforms.validators import DataRequired, EqualTo, Length, Optional, Regexp
from wtforms.validators import ValidationError

from trampomatch.forms.candidato import (
    DISPONIBILIDADES,
    EXTENSOES_CURRICULO,
    HABILIDADES_PREDEFINIDAS,
    LIMITE_CURRICULO_BYTES,
    NIVEIS_EXPERIENCIA,
    TIPOS_TRABALHO,
)

EMAIL_BASICO = Regexp(
    r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    message="Informe um e-mail válido.",
)


class CadastroForm(FlaskForm):
    nome = StringField("Nome", validators=[DataRequired(), Length(min=3, max=100)])
    email = EmailField(
        "E-mail", validators=[DataRequired(), EMAIL_BASICO, Length(max=150)]
    )
    senha = PasswordField("Senha", validators=[DataRequired(), Length(min=6)])
    confirmar_senha = PasswordField(
        "Confirmar senha",
        validators=[DataRequired(), EqualTo("senha", message="Senhas não conferem.")],
    )
    tipo_perfil = RadioField(
        "Tipo de perfil",
        choices=[("candidato", "Candidato"), ("contratante", "Contratante")],
        default="candidato",
        validators=[DataRequired()],
    )
    submit = SubmitField("Cadastrar")


class LoginForm(FlaskForm):
    email = EmailField(
        "E-mail", validators=[DataRequired(), EMAIL_BASICO, Length(max=150)]
    )
    senha = PasswordField("Senha", validators=[DataRequired()])
    submit = SubmitField("Entrar")


TIPOS_CONTRATANTE = [
    ("empresa", "Empresa"),
    ("pessoa_fisica", "Pessoa física"),
]

QUANTIDADES_FUNCIONARIOS = [
    ("1-10", "1 - 10"),
    ("11-50", "11 - 50"),
    ("51-200", "51 - 200"),
    ("200+", "200+"),
]

AREAS_ATUACAO_PREDEFINIDAS = [
    "Construção Civil",
    "Limpeza",
    "Logística",
    "Comércio",
    "Tecnologia",
    "Serviços",
]

TAMANHO_MAX_LOGO = 2 * 1024 * 1024


def normalizar_areas_atuacao(valor):
    partes = [parte.strip() for parte in (valor or "").split(",")]
    areas = []
    for parte in partes:
        if not parte or parte.lower() in {area.lower() for area in areas}:
            continue
        areas.append(parte[:40])
        if len(areas) == 3:
            break
    return ", ".join(areas)


def validar_logo_empresa(form, field):
    arquivo = field.data
    if not arquivo or not getattr(arquivo, "filename", ""):
        return

    extensao = (
        arquivo.filename.rsplit(".", 1)[-1].lower() if "." in arquivo.filename else ""
    )
    if extensao not in {"png", "jpg", "jpeg"}:
        raise ValidationError("Envie uma imagem PNG ou JPG.")

    posicao_atual = arquivo.stream.tell()
    arquivo.stream.seek(0, 2)
    tamanho = arquivo.stream.tell()
    arquivo.stream.seek(posicao_atual)

    if tamanho > TAMANHO_MAX_LOGO:
        raise ValidationError("A logo deve ter no máximo 2 MB.")


class GoogleContratanteOnboardingForm(FlaskForm):
    logo_empresa = FileField(
        "Logo da empresa",
        validators=[
            validar_logo_empresa,
        ],
    )
    nome_empresa = StringField(
        "Nome da empresa",
        validators=[DataRequired(), Length(max=150)],
    )
    regiao = StringField("Região", validators=[DataRequired(), Length(max=100)])
    descricao = TextAreaField(
        "Descrição da empresa",
        validators=[DataRequired(), Length(max=500)],
    )
    tipo_contratante = RadioField(
        "Tipo de contratante",
        choices=TIPOS_CONTRATANTE,
        default="empresa",
        validators=[DataRequired()],
    )
    quantidade_funcionarios = RadioField(
        "Quantidade de funcionários",
        choices=QUANTIDADES_FUNCIONARIOS,
        default="1-10",
        validators=[DataRequired()],
    )
    areas_atuacao = HiddenField(
        "Áreas de atuação",
        validators=[Optional(), Length(max=500)],
    )
    site = StringField("Site ou rede social", validators=[Optional(), Length(max=200)])
    submit = SubmitField("Salvar perfil")


class GoogleCandidatoOnboardingForm(FlaskForm):
    regiao = StringField("Região", validators=[DataRequired(), Length(max=100)])
    tipo_trabalho = SelectField(
        "Tipo de trabalho desejado",
        choices=TIPOS_TRABALHO,
        validators=[DataRequired()],
    )
    disponibilidade = SelectField(
        "Disponibilidade",
        choices=DISPONIBILIDADES,
        validators=[DataRequired(), Length(max=100)],
    )
    habilidades = TextAreaField(
        "Habilidades",
        default=", ".join(HABILIDADES_PREDEFINIDAS[:2]),
        validators=[DataRequired()],
    )
    experiencia_resumida = TextAreaField(
        "Experiência resumida",
        validators=[Optional(), Length(max=1000)],
    )
    nivel_experiencia = SelectField(
        "Nível de experiência",
        choices=NIVEIS_EXPERIENCIA,
        coerce=int,
        default=30,
        validators=[DataRequired()],
    )
    curriculo = FileField(
        "Currículo",
        validators=[
            FileAllowed(
                EXTENSOES_CURRICULO,
                "Envie um arquivo PDF, DOC ou DOCX.",
            ),
            FileSize(
                max_size=LIMITE_CURRICULO_BYTES,
                message="O currículo deve ter no máximo 5MB.",
            ),
        ],
    )
    submit = SubmitField("Salvar perfil")
