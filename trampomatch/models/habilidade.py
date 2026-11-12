from trampomatch.extensions import db


class Habilidade(db.Model):
    __tablename__ = "habilidades"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)

    def __repr__(self):
        return f"<Habilidade {self.nome}>"
