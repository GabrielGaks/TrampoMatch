from trampomatch.forms.auth import CadastroForm, GoogleCandidatoOnboardingForm
from trampomatch.forms.auth import GoogleContratanteOnboardingForm, LoginForm
from trampomatch.forms.candidato import (
    CurriculoCandidatoForm,
    FiltroCandidatoForm,
    PerfilCandidatoForm,
)
from trampomatch.forms.contratante import MensagemMatchForm, PerfilContratanteForm
from trampomatch.forms.vagas import FiltroVagaForm, VagaForm

__all__ = [
    "CadastroForm",
    "CurriculoCandidatoForm",
    "FiltroCandidatoForm",
    "FiltroVagaForm",
    "GoogleCandidatoOnboardingForm",
    "GoogleContratanteOnboardingForm",
    "LoginForm",
    "MensagemMatchForm",
    "PerfilCandidatoForm",
    "PerfilContratanteForm",
    "VagaForm",
]
