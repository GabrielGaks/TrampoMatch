from trampomatch.extensions import db
from trampomatch.models import PerfilCandidato, PerfilContratante, Usuario, Vaga


def criar_usuario(nome="Usuário Teste", email="user@test.com", tipo="candidato"):
    usuario = Usuario(nome=nome, email=email, tipo_perfil=tipo)
    usuario.set_senha("senha123")
    db.session.add(usuario)
    db.session.commit()
    return usuario


def criar_candidato(
    email="candidato@test.com",
    com_perfil=True,
    nome="Candidato Teste",
    **perfil_kwargs,
):
    usuario = criar_usuario(nome, email, "candidato")
    if com_perfil:
        dados = {
            "usuario_id": usuario.id,
            "regiao": "Vitória",
            "tipo_trabalho": "diaria",
            "disponibilidade": "manhã",
            "habilidades": "limpeza, organização",
            "experiencia_resumida": "Experiência em serviços gerais.",
            "nivel_experiencia": 45,
        }
        dados.update(perfil_kwargs)
        perfil = PerfilCandidato(**dados)
        db.session.add(perfil)
        db.session.commit()
    return usuario


def criar_contratante(email="contratante@test.com", com_perfil=True):
    usuario = criar_usuario("Contratante Teste", email, "contratante")
    if com_perfil:
        perfil = PerfilContratante(
            usuario_id=usuario.id,
            regiao="Vitória",
            descricao="Pequeno negócio local.",
        )
        db.session.add(perfil)
        db.session.commit()
    return usuario


def criar_vaga(contratante, **kwargs):
    dados = {
        "contratante_id": contratante.id,
        "titulo": "Auxiliar de Serviços Gerais",
        "descricao": "Limpeza e organização.",
        "regiao": "Vitória",
        "tipo_vaga": "diaria",
        "valor_min": 120,
        "valor_max": 150,
        "habilidades_desejadas": "limpeza, organização",
        "complexidade": 45,
        "status": "aberta",
    }
    dados.update(kwargs)
    vaga = Vaga(**dados)
    db.session.add(vaga)
    db.session.commit()
    return vaga


def login(client, email, senha="senha123"):
    return client.post(
        "/auth/login",
        data={"email": email, "senha": senha},
        follow_redirects=False,
    )
