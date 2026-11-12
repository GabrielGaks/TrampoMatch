from trampomatch.views.auth import bp_auth
from trampomatch.views.candidato import bp_candidato
from trampomatch.views.contratante import bp_contratante
from trampomatch.views.main import bp_main
from trampomatch.views.vagas import bp_vagas


def init_app(app):
    app.register_blueprint(bp_main)
    app.register_blueprint(bp_auth)
    app.register_blueprint(bp_candidato)
    app.register_blueprint(bp_contratante)
    app.register_blueprint(bp_vagas)
    app.logger.info("Blueprint 'main' registrado com sucesso")
