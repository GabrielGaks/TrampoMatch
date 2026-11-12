from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Iterable

try:
    from rapidfuzz import fuzz, process

    TEM_RAPIDFUZZ = True
except Exception:  # pragma: no cover
    TEM_RAPIDFUZZ = False


def _valor(objeto, nome, padrao=None):
    if isinstance(objeto, dict):
        return objeto.get(nome, padrao)
    return getattr(objeto, nome, padrao)


def _normalizar(texto) -> str:
    if texto is None:
        return ""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.lower().split())


def _lista_normalizada(valor) -> list[str]:
    if valor is None:
        return []
    if isinstance(valor, str):
        partes = valor.replace(";", ",").split(",")
    elif isinstance(valor, (list, tuple, set)):
        partes = list(valor)
    else:
        partes = [valor]
    return [item for item in (_normalizar(parte) for parte in partes) if item]


def _clamp(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, valor))


NIVEIS_LABEL = {
    "iniciante": 20,
    "basico": 30,
    "junior": 35,
    "estagio": 25,
    "intermediario": 55,
    "pleno": 65,
    "avancado": 80,
    "senior": 85,
    "especialista": 95,
    "expert": 95,
}

NIVEIS_EXPERIENCIA_CATEGORIAS = (
    {"slug": "iniciante", "rotulo": "Iniciante", "min": 0, "max": 25, "ordem": 1},
    {"slug": "junior", "rotulo": "Junior", "min": 26, "max": 45, "ordem": 2},
    {"slug": "pleno", "rotulo": "Pleno", "min": 46, "max": 70, "ordem": 3},
    {"slug": "senior", "rotulo": "Senior", "min": 71, "max": 85, "ordem": 4},
    {
        "slug": "especialista",
        "rotulo": "Especialista",
        "min": 86,
        "max": 100,
        "ordem": 5,
    },
)

COMPLEXIDADE_CATEGORIAS = (
    {"slug": "simples", "rotulo": "Simples", "min": 0, "max": 30, "ordem": 1},
    {"slug": "moderada", "rotulo": "Moderada", "min": 31, "max": 55, "ordem": 2},
    {"slug": "alta", "rotulo": "Alta", "min": 56, "max": 80, "ordem": 3},
    {
        "slug": "especializada",
        "rotulo": "Especializada",
        "min": 81,
        "max": 100,
        "ordem": 4,
    },
)


def _num(valor) -> float:
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = _normalizar(valor)
    if texto in NIVEIS_LABEL:
        return float(NIVEIS_LABEL[texto])
    try:
        return float(texto.replace(",", "."))
    except ValueError:
        return 0.0


def _categoria_por_valor(valor, categorias: tuple[dict, ...]) -> dict:
    numero = _clamp(_num(valor), 0, 100)
    for categoria in categorias:
        if categoria["min"] <= numero <= categoria["max"]:
            return categoria
    return categorias[0]


CLUSTERS_REGIAO: dict[str, set[str]] = {
    "grande_vitoria": {
        "vitoria",
        "vila velha",
        "serra",
        "cariacica",
        "viana",
        "fundao",
        "guarapari",
    },
}

PROXIMIDADE_REGIAO: dict[tuple[str, str], float] = {}


def _cluster_de(regiao: str) -> str | None:
    for nome, membros in CLUSTERS_REGIAO.items():
        if regiao in membros:
            return nome
    return None


def score_regiao(regiao_candidato, regiao_vaga, peso_cluster: float = 0.6) -> float:
    candidato = _normalizar(regiao_candidato)
    vaga = _normalizar(regiao_vaga)
    if not candidato or not vaga:
        return 0.0
    if candidato == vaga:
        return 1.0

    par = tuple(sorted((candidato, vaga)))
    if par in PROXIMIDADE_REGIAO:
        return PROXIMIDADE_REGIAO[par]

    cluster_candidato = _cluster_de(candidato)
    cluster_vaga = _cluster_de(vaga)
    if cluster_candidato is not None and cluster_candidato == cluster_vaga:
        return peso_cluster
    return 0.0


def score_tipo(tipo_candidato, tipo_vaga) -> float:
    vaga = _normalizar(tipo_vaga)
    if not vaga:
        return 1.0

    candidatos = set(_lista_normalizada(tipo_candidato))
    if not candidatos:
        return 0.0
    if candidatos & {"qualquer", "todos", "flexivel"}:
        return 1.0
    return 1.0 if vaga in candidatos else 0.0


def categoria_experiencia(nivel) -> dict:
    return _categoria_por_valor(nivel, NIVEIS_EXPERIENCIA_CATEGORIAS)


def categoria_complexidade(complexidade) -> dict:
    return _categoria_por_valor(complexidade, COMPLEXIDADE_CATEGORIAS)


def score_experiencia(nivel, complexidade) -> float:
    experiencia = categoria_experiencia(nivel)
    exigencia = categoria_complexidade(complexidade)
    diferenca = experiencia["ordem"] - exigencia["ordem"]

    if diferenca == 0:
        return 1.0
    if diferenca > 0:
        return {1: 0.95, 2: 0.9}.get(diferenca, 0.85)
    return {-1: 0.72, -2: 0.42}.get(diferenca, 0.15)


SINONIMOS_HABILIDADES: dict[str, str] = {
    "dirigir": "conducao",
    "direcao": "conducao",
    "motorista": "conducao",
    "cnh": "conducao",
    "entrega": "entregas",
    "entregas": "entregas",
    "limpeza": "limpeza",
    "faxina": "limpeza",
    "limpar": "limpeza",
    "organizacao": "organizacao",
    "organizar": "organizacao",
    "atendimento": "atendimento",
    "atendimento ao cliente": "atendimento",
    "recepcao": "atendimento",
    "vendas": "vendas",
    "vendedor": "vendas",
    "vendedora": "vendas",
    "cozinha": "cozinha",
    "cozinhar": "cozinha",
    "cozinheiro": "cozinha",
    "cozinheira": "cozinha",
    "garcom": "garcom",
    "garcon": "garcom",
    "garconete": "garcom",
    "cuidador": "cuidados",
    "cuidadora": "cuidados",
    "cuidados": "cuidados",
    "baba": "cuidados",
}


def _canonizar(habilidade: str) -> str:
    return SINONIMOS_HABILIDADES.get(habilidade, habilidade)


def _conjunto_canonico(habilidades) -> set[str]:
    return {_canonizar(habilidade) for habilidade in _lista_normalizada(habilidades)}


def score_habilidades(
    habilidades_candidato,
    habilidades_exigidas,
    usar_fuzzy: bool = True,
    limiar_fuzzy: int = 88,
) -> tuple[float, set[str], set[str]]:
    exigidas = _conjunto_canonico(habilidades_exigidas)
    if not exigidas:
        return 1.0, set(), set()

    possui = _conjunto_canonico(habilidades_candidato)
    cobertas = exigidas & possui
    faltantes = exigidas - possui

    if usar_fuzzy and TEM_RAPIDFUZZ and faltantes and possui:
        ainda_faltam: set[str] = set()
        for requerida in faltantes:
            achou = process.extractOne(requerida, list(possui), scorer=fuzz.ratio)
            if achou and achou[1] >= limiar_fuzzy:
                cobertas.add(requerida)
            else:
                ainda_faltam.add(requerida)
        faltantes = ainda_faltam

    return len(cobertas) / len(exigidas), cobertas, faltantes


def _expandir_turnos(turnos: set[str]) -> set[str]:
    expandidos = set(turnos)
    if expandidos & {"integral", "flexivel", "qualquer", "todos"}:
        expandidos |= {"manha", "tarde", "noite", "fins de semana"}
    if "fim de semana" in expandidos:
        expandidos.add("fins de semana")
    return expandidos


def score_disponibilidade(
    disponibilidade_candidato, disponibilidade_exigida
) -> tuple[float, set[str]]:
    exigida = _expandir_turnos(set(_lista_normalizada(disponibilidade_exigida)))
    if not exigida:
        return 1.0, set()

    oferta = _expandir_turnos(set(_lista_normalizada(disponibilidade_candidato)))
    cobertos = exigida & oferta
    return len(cobertos) / len(exigida), exigida - oferta


@dataclass
class PesosCompatibilidade:
    regiao: float = 0.05
    tipo: float = 0.05
    habilidades: float = 0.80
    experiencia: float = 0.05
    disponibilidade: float = 0.05

    @property
    def total(self) -> float:
        return (
            self.regiao
            + self.tipo
            + self.habilidades
            + self.experiencia
            + self.disponibilidade
        )


@dataclass
class ConfigCompatibilidade:
    pesos: PesosCompatibilidade = field(default_factory=PesosCompatibilidade)
    exige_regiao_alcancavel: bool = True
    exige_turno_compativel: bool = True
    cobertura_minima_habilidades: float = 0.0
    limiar_compativel: float = 70.0


@dataclass
class CriterioResultado:
    nome: str
    peso: float
    score: float
    contribuicao: float
    detalhe: str = ""


@dataclass
class ResultadoCompatibilidade:
    score: float
    elegivel: bool
    criterios: list[CriterioResultado]
    resumo: str
    bloqueios: list[str] = field(default_factory=list)

    @property
    def compativel(self) -> bool:
        return self.elegivel and self.score >= 70.0

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "elegivel": self.elegivel,
            "resumo": self.resumo,
            "bloqueios": self.bloqueios,
            "criterios": [
                {
                    "nome": criterio.nome,
                    "peso": round(criterio.peso, 3),
                    "score": round(criterio.score, 3),
                    "contribuicao": round(criterio.contribuicao, 1),
                    "detalhe": criterio.detalhe,
                }
                for criterio in self.criterios
            ],
        }


def calcular_compatibilidade(
    perfil,
    vaga,
    config: ConfigCompatibilidade | None = None,
) -> ResultadoCompatibilidade:
    cfg = config or ConfigCompatibilidade()
    pesos = cfg.pesos

    regiao = score_regiao(_valor(perfil, "regiao"), _valor(vaga, "regiao"))
    tipo = score_tipo(_valor(perfil, "tipo_trabalho"), _valor(vaga, "tipo_vaga"))
    habilidades, cobertas, faltantes = score_habilidades(
        _valor(perfil, "habilidades"),
        _valor(vaga, "habilidades_desejadas"),
    )
    vaga_tem_habilidades = bool(
        _conjunto_canonico(_valor(vaga, "habilidades_desejadas"))
    )
    experiencia = score_experiencia(
        _valor(perfil, "nivel_experiencia", 0),
        _valor(vaga, "complexidade", 0),
    )
    disponibilidade, turnos_faltantes = score_disponibilidade(
        _valor(perfil, "disponibilidade"),
        _valor(vaga, "disponibilidade"),
    )

    criterios = [
        CriterioResultado(
            "regiao",
            pesos.regiao,
            regiao,
            pesos.regiao * regiao * 100,
            _detalhe_regiao(regiao),
        ),
        CriterioResultado(
            "tipo",
            pesos.tipo,
            tipo,
            pesos.tipo * tipo * 100,
            "Tipo compativel" if tipo else "Tipo diferente",
        ),
        CriterioResultado(
            "habilidades",
            pesos.habilidades,
            habilidades,
            pesos.habilidades * habilidades * 100,
            _detalhe_habilidades(cobertas, faltantes),
        ),
        CriterioResultado(
            "experiencia",
            pesos.experiencia,
            experiencia,
            pesos.experiencia * experiencia * 100,
            _detalhe_experiencia(perfil, vaga),
        ),
        CriterioResultado(
            "disponibilidade",
            pesos.disponibilidade,
            disponibilidade,
            pesos.disponibilidade * disponibilidade * 100,
            _detalhe_disponibilidade(disponibilidade, turnos_faltantes),
        ),
    ]

    score_bruto = round(
        sum(criterio.contribuicao for criterio in criterios) / pesos.total, 1
    )
    if vaga_tem_habilidades:
        teto = round(15 + habilidades * 85, 1)
        score = min(score_bruto, teto)
    else:
        score = score_bruto

    bloqueios: list[str] = []
    if cfg.exige_regiao_alcancavel and regiao <= 0:
        bloqueios.append("Regiao fora de alcance")
    if cfg.exige_turno_compativel and disponibilidade <= 0:
        bloqueios.append("Sem turno em comum")
    if habilidades < cfg.cobertura_minima_habilidades:
        bloqueios.append("Habilidades essenciais ausentes")

    elegivel = not bloqueios
    return ResultadoCompatibilidade(
        score=score,
        elegivel=elegivel,
        criterios=criterios,
        resumo=_montar_resumo(
            score, elegivel, criterios, bloqueios, vaga_tem_habilidades
        ),
        bloqueios=bloqueios,
    )


def _detalhe_regiao(score: float) -> str:
    if score >= 1.0:
        return "Mesma regiao"
    if score > 0:
        return "Regiao vizinha no mesmo polo metropolitano"
    return "Regiao distante"


def _detalhe_habilidades(cobertas: set[str], faltantes: set[str]) -> str:
    total = len(cobertas) + len(faltantes)
    if total == 0:
        return "Vaga sem habilidades especificas"
    texto = f"{len(cobertas)}/{total} habilidades exigidas"
    if faltantes:
        texto += f"; falta: {', '.join(sorted(faltantes))}"
    return texto


def _detalhe_experiencia(perfil, vaga) -> str:
    experiencia = categoria_experiencia(_valor(perfil, "nivel_experiencia", 0))
    complexidade = categoria_complexidade(_valor(vaga, "complexidade", 0))
    if experiencia["ordem"] >= complexidade["ordem"]:
        return (
            f"Experiencia {experiencia['rotulo']} atende "
            f"complexidade {complexidade['rotulo']}"
        )
    return (
        f"Experiencia {experiencia['rotulo']} abaixo de "
        f"complexidade {complexidade['rotulo']}"
    )


def _detalhe_disponibilidade(score: float, faltantes: set[str]) -> str:
    if not faltantes and score >= 1.0:
        return "Cobre todos os turnos exigidos"
    if score <= 0:
        return "Nenhum turno em comum"
    return f"Cobre parte dos turnos; falta: {', '.join(sorted(faltantes))}"


def _montar_resumo(
    score: float,
    elegivel: bool,
    criterios: list[CriterioResultado],
    bloqueios: list[str],
    vaga_tem_habilidades: bool = False,
) -> str:
    if not elegivel:
        return "Incompativel: " + "; ".join(bloqueios)

    criterio_habilidades = next(
        (criterio for criterio in criterios if criterio.nome == "habilidades"),
        None,
    )
    if vaga_tem_habilidades and criterio_habilidades:
        forte = criterio_habilidades
        fraco = criterio_habilidades
        resumo = f"{score:.0f}% de match; habilidades {forte.score * 100:.0f}%"
        if fraco.score < 0.6:
            resumo += "; habilidades abaixo do ideal"
        return resumo

    forte = max(criterios, key=lambda criterio: criterio.contribuicao)
    fraco = min(criterios, key=lambda criterio: criterio.score)
    resumo = f"{score:.0f}% de match; forte em {forte.nome}"
    if fraco.score < 0.6:
        resumo += f", ponto fraco: {fraco.nome}"
    return resumo


def _idade_em_dias(vaga, hoje: date | None) -> int:
    hoje = hoje or date.today()
    data_inicio = _valor(vaga, "data_inicio")
    criado_em = _valor(vaga, "criado_em")
    data_referencia = data_inicio or criado_em
    if isinstance(data_referencia, datetime):
        data_referencia = data_referencia.date()
    if isinstance(data_referencia, date):
        return max(0, (hoje - data_referencia).days)
    return 999


def ordenar_por_recomendacao(
    pares: Iterable[tuple[object, ResultadoCompatibilidade]],
    hoje: date | None = None,
) -> list[tuple[object, ResultadoCompatibilidade]]:
    return sorted(
        pares,
        key=lambda par: (
            not par[1].elegivel,
            -par[1].score,
            _idade_em_dias(par[0], hoje),
        ),
    )


def vaga_compativel(
    resultado: ResultadoCompatibilidade,
    limiar: float = 70.0,
) -> bool:
    return resultado.elegivel and resultado.score >= limiar


def compatibilidade(perfil, vaga) -> float:
    return calcular_compatibilidade(perfil, vaga).score
