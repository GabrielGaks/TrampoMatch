from flask import Blueprint, current_app, redirect, render_template, url_for
from flask_login import current_user

bp_main = Blueprint("main", __name__)


@bp_main.route("/")
@bp_main.route("/index")
def index():
    current_app.logger.debug("Acesso registrado à página inicial")
    if current_user.is_authenticated:
        if current_user.eh_candidato:
            destino = (
                "candidato.dashboard"
                if current_user.perfil_candidato
                else "candidato.perfil"
            )
        else:
            destino = (
                "contratante.dashboard"
                if current_user.perfil_contratante
                else "contratante.perfil"
            )
        return redirect(url_for(destino))

    metricas = [
        {"numero": "Grátis", "rotulo": "para candidatos"},
        {"numero": "Sua cidade", "rotulo": "vagas por região"},
        {"numero": "Sem app", "rotulo": "acessa pelo navegador"},
    ]

    criterios_compatibilidade = [
        {"titulo": "Região",          "descricao": "Sua cidade em primeiro lugar."},
        {"titulo": "Tipo de trabalho", "descricao": "Diária, temporário ou contrato."},
        {"titulo": "Disponibilidade", "descricao": "Manhã, tarde ou noite — sem conflito."},
        {"titulo": "Habilidades",     "descricao": "Quanto mais batem, maior o %."},
        {"titulo": "Experiência",     "descricao": "Vaga no seu nível, sem chute."},
        {"titulo": "Nível da vaga",   "descricao": "Simples a especializada, sempre claro."},
    ]

    demo_candidato = {
        "vaga": {
            "titulo": "Auxiliar de Limpeza",
            "empresa": "Empresa Confiança",
            "regiao": "Vila Velha, ES",
            "tipo_vaga": "Diária",
            "valor": "R$ 120 / dia",
            "compatibilidade": 91,
            "habilidades": ["Limpeza", "Organização", "Pontualidade"],
        }
    }

    demo_contratante = {
        "vaga": "Pedreiro",
        "regiao": "Serra, ES",
        "candidatos": [
            {
                "nome": "Carlos M.",
                "regiao": "Serra",
                "nivel": "Pleno",
                "compatibilidade": 94,
            },
            {
                "nome": "Roberto S.",
                "regiao": "Cariacica",
                "nivel": "Sênior",
                "compatibilidade": 88,
            },
            {
                "nome": "João P.",
                "regiao": "Vitória",
                "nivel": "Júnior",
                "compatibilidade": 76,
            },
        ],
    }

    return render_template(
        "main/index.html",
        criterios_compatibilidade=criterios_compatibilidade,
        demo_candidato=demo_candidato,
        demo_contratante=demo_contratante,
        metricas=metricas,
    )
