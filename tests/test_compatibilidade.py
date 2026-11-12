from trampomatch.services import calcular_compatibilidade, compatibilidade


def test_compatibilidade_perfeita():
    perfil = {
        "regiao": "Vitória",
        "tipo_trabalho": "diaria",
        "habilidades": ["limpeza", "organização"],
        "nivel_experiencia": 20,
    }
    vaga = {
        "regiao": "Vitória",
        "tipo_vaga": "diaria",
        "habilidades_desejadas": ["limpeza", "organização"],
        "complexidade": 20,
    }
    resultado = calcular_compatibilidade(perfil, vaga)
    assert resultado.score == 100.0
    assert resultado.elegivel is True
    assert resultado.compativel is True


def test_compatibilidade_parcial():
    perfil = {
        "regiao": "Vitória",
        "tipo_trabalho": "diaria",
        "habilidades": ["limpeza"],
        "nivel_experiencia": 50,
    }
    vaga = {
        "regiao": "Vitória",
        "tipo_vaga": "temporario",
        "habilidades_desejadas": ["limpeza", "organização"],
        "complexidade": 70,
    }
    resultado = calcular_compatibilidade(perfil, vaga)
    assert resultado.score == 55.0
    assert resultado.elegivel is True
    assert resultado.compativel is False


def test_compatibilidade_sem_match_de_regiao():
    perfil = {
        "regiao": "Linhares",
        "tipo_trabalho": "diaria",
        "habilidades": ["limpeza"],
        "nivel_experiencia": 20,
    }
    vaga = {
        "regiao": "Vitoria",
        "tipo_vaga": "diaria",
        "habilidades_desejadas": ["limpeza"],
        "complexidade": 20,
    }
    resultado = calcular_compatibilidade(perfil, vaga)
    assert resultado.score == 95.0
    assert resultado.elegivel is False
    assert resultado.bloqueios == ["Regiao fora de alcance"]


def test_regiao_metropolitana_tem_match_parcial():
    perfil = {
        "regiao": "Vila Velha",
        "tipo_trabalho": "diaria",
        "disponibilidade": "manha",
        "habilidades": ["limpeza"],
        "nivel_experiencia": 50,
    }
    vaga = {
        "regiao": "Vitoria",
        "tipo_vaga": "diaria",
        "disponibilidade": "manha",
        "habilidades_desejadas": ["limpeza"],
        "complexidade": 50,
    }

    resultado = calcular_compatibilidade(perfil, vaga)

    assert resultado.elegivel is True
    assert resultado.score == 97.8


def test_disponibilidade_sem_turno_em_comum_bloqueia():
    perfil = {
        "regiao": "Vitória",
        "tipo_trabalho": "diaria",
        "disponibilidade": "noite",
        "habilidades": ["limpeza"],
        "nivel_experiencia": 50,
    }
    vaga = {
        "regiao": "Vitória",
        "tipo_vaga": "diaria",
        "disponibilidade": "manha",
        "habilidades_desejadas": ["limpeza"],
        "complexidade": 50,
    }

    resultado = calcular_compatibilidade(perfil, vaga)

    assert resultado.elegivel is False
    assert resultado.bloqueios == ["Sem turno em comum"]
    assert compatibilidade(perfil, vaga) == resultado.score


def test_habilidades_dominam_match():
    perfil = {
        "regiao": "Vila Velha",
        "tipo_trabalho": "diaria",
        "disponibilidade": "integral",
        "habilidades": ["programacao", "full stack", "python", "javascript"],
        "nivel_experiencia": 90,
    }
    vaga = {
        "regiao": "Vila Velha",
        "tipo_vaga": "diaria",
        "disponibilidade": "integral",
        "habilidades_desejadas": ["pedreiro", "alvenaria", "revestimento"],
        "complexidade": 40,
    }

    resultado = calcular_compatibilidade(perfil, vaga)

    assert resultado.elegivel is True
    assert resultado.score <= 20.0
    assert "habilidades" in resultado.resumo.lower()
