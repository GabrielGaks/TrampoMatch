from authlib.integrations.flask_client import OAuth
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()
csrf = CSRFProtect()
oauth = OAuth()

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Você precisa estar logado para acessar esta página."
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id):
    try:
        from trampomatch.models.usuario import Usuario
    except ModuleNotFoundError as exc:
        if exc.name != "trampomatch.models.usuario":
            raise
        return None

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return None

    return db.session.get(Usuario, user_id)
