from flask_wtf import FlaskForm
from wtforms import BooleanField, EmailField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, Regexp

EMAIL_BASICO = Regexp(
    r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    message="Informe um e-mail válido.",
)


class PerfilContratanteForm(FlaskForm):
    regiao = StringField("Região", validators=[DataRequired(), Length(max=100)])
    descricao = TextAreaField("Descrição", validators=[Optional()])
    submit = SubmitField("Salvar perfil")


class MensagemMatchForm(FlaskForm):
    mensagem = TextAreaField(
        "Mensagem para o candidato",
        validators=[DataRequired(), Length(max=1000)],
    )
    usar_email = BooleanField("Usar Gmail/e-mail")
    contato_email = EmailField(
        "Gmail/e-mail",
        validators=[Optional(), EMAIL_BASICO, Length(max=150)],
    )
    usar_telefone = BooleanField("Usar telefone")
    contato_telefone = StringField(
        "Telefone",
        validators=[Optional(), Length(max=30)],
    )
    submit = SubmitField("Salvar mensagem")

    def validate(self, extra_validators=None):
        valido = super().validate(extra_validators=extra_validators)
        if not valido:
            return False

        email = (self.contato_email.data or "").strip()
        telefone = (self.contato_telefone.data or "").strip()
        valido = True

        if not self.usar_email.data and not self.usar_telefone.data:
            mensagem = "Selecione pelo menos um meio de contato."
            self.usar_email.errors.append(mensagem)
            self.usar_telefone.errors.append(mensagem)
            valido = False

        if self.usar_email.data and not email:
            self.contato_email.errors.append("Informe o e-mail de contato.")
            valido = False

        if self.usar_telefone.data and not telefone:
            self.contato_telefone.errors.append("Informe o telefone de contato.")
            valido = False

        self.contato_email.data = email if self.usar_email.data else ""
        self.contato_telefone.data = telefone if self.usar_telefone.data else ""
        return valido
