from flask_wtf import FlaskForm
from wtforms import DateField, FloatField, SelectField, StringField
from wtforms import SubmitField, TextAreaField
from wtforms.validators import (
    DataRequired,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)

from trampomatch.forms.candidato import CATEGORIAS_TRABALHO
from trampomatch.models.vaga import COMPLEXIDADE_CATEGORIAS

TIPOS_VAGA = [
    ("diaria", "Diária"),
    ("temporario", "Temporário"),
    ("contrato", "Contrato"),
]

STATUS_VAGA = [("aberta", "Aberta"), ("encerrada", "Encerrada")]

DISPONIBILIDADES_VAGA = [
    ("", "Sem exigência"),
    ("manhã", "Manhã"),
    ("tarde", "Tarde"),
    ("noite", "Noite"),
    ("integral", "Integral"),
    ("fins de semana", "Fins de semana"),
    ("flexível", "Flexível"),
]

COMPLEXIDADES_VAGA = [
    (categoria["valor"], categoria["rotulo"]) for categoria in COMPLEXIDADE_CATEGORIAS
]

FILTROS_COMPLEXIDADE = [
    (categoria["slug"], categoria["rotulo"]) for categoria in COMPLEXIDADE_CATEGORIAS
]


class VagaForm(FlaskForm):
    titulo = StringField("Título", validators=[DataRequired(), Length(max=150)])
    categoria = SelectField(
        "Categoria da vaga",
        choices=[("", "Selecione uma categoria...")] + CATEGORIAS_TRABALHO,
        validators=[DataRequired()],
    )
    descricao = TextAreaField("Descrição", validators=[DataRequired()])
    regiao = StringField("Região", validators=[DataRequired(), Length(max=100)])
    tipo_vaga = SelectField(
        "Tipo de vaga", choices=TIPOS_VAGA, validators=[DataRequired()]
    )
    disponibilidade = SelectField(
        "Disponibilidade exigida",
        choices=DISPONIBILIDADES_VAGA,
        validators=[Optional(), Length(max=120)],
    )
    valor_min = FloatField("Valor mínimo", validators=[Optional(), NumberRange(min=0)])
    valor_max = FloatField("Valor máximo", validators=[Optional(), NumberRange(min=0)])
    data_inicio = DateField("Data início", validators=[Optional()])
    data_fim = DateField("Data fim", validators=[Optional()])
    habilidades_desejadas = TextAreaField(
        "Habilidades desejadas", validators=[DataRequired()]
    )
    complexidade = SelectField(
        "Nível da vaga",
        choices=COMPLEXIDADES_VAGA,
        coerce=int,
        validators=[DataRequired(), NumberRange(min=1, max=100)],
    )
    status = SelectField("Status", choices=STATUS_VAGA, default="aberta")
    submit = SubmitField("Salvar vaga")

    def validate_valor_max(self, field):
        if self.valor_min.data is not None and field.data is not None:
            if field.data < self.valor_min.data:
                raise ValidationError("Valor máximo deve ser maior ou igual ao mínimo.")


class FiltroVagaForm(FlaskForm):
    regiao = StringField("Região", validators=[Optional(), Length(max=100)])
    categoria = SelectField(
        "Categoria",
        choices=[("", "Todas as categorias"), *CATEGORIAS_TRABALHO],
        validators=[Optional()],
    )
    tipo_vaga = SelectField(
        "Tipo",
        choices=[("", "Todos"), *TIPOS_VAGA],
        validators=[Optional()],
    )
    complexidade = SelectField(
        "Nível da vaga",
        choices=[("", "Todas"), *FILTROS_COMPLEXIDADE],
        validators=[Optional()],
    )
    status = SelectField(
        "Status",
        choices=[("", "Todas"), *STATUS_VAGA],
        validators=[Optional()],
    )
    submit = SubmitField("Filtrar")
