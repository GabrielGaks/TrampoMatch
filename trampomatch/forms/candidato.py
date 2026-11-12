from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired, FileSize
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

EXTENSOES_CURRICULO = ["pdf", "doc", "docx"]
LIMITE_CURRICULO_BYTES = 5 * 1024 * 1024

TIPOS_TRABALHO = [
    ("diaria", "Diária"),
    ("temporario", "Temporário"),
    ("contrato", "Contrato"),
]

CATEGORIAS_TRABALHO = [
    ("tecnologia",     "Tecnologia / TI"),
    ("administrativo", "Administrativo / Escritório"),
    ("comercio_vendas", "Comércio / Vendas"),
    ("servicos_gerais", "Serviços Gerais / Limpeza"),
    ("construcao",     "Construção Civil / Reformas"),
    ("transporte",     "Transporte / Entregas / Logística"),
    ("alimentacao",    "Alimentação / Gastronomia"),
    ("saude",          "Saúde / Bem-estar"),
    ("educacao",       "Educação / Ensino"),
    ("seguranca",      "Segurança / Vigilância"),
    ("beleza",         "Beleza / Estética"),
    ("industria",      "Indústria / Manufatura"),
    ("eventos",        "Eventos / Entretenimento"),
    ("comunicacao",    "Comunicação / Marketing / Design"),
    ("juridico",       "Jurídico / Contabilidade / Finanças"),
    ("outro",          "Outro"),
]

DISPONIBILIDADES = [
    ("manhã", "Manhã"),
    ("tarde", "Tarde"),
    ("noite", "Noite"),
    ("integral", "Integral"),
    ("fins de semana", "Fins de semana"),
    ("flexível", "Flexível"),
]

REGIOES_GRANDE_VITORIA = [
    # Espírito Santo
    "Vitória",
    "Vila Velha",
    "Serra",
    "Cariacica",
    "Viana",
    "Guarapari",
    "Fundão",
    "Aracruz",
    "Cachoeiro de Itapemirim",
    "Colatina",
    "Linhares",
    "São Mateus",
    # São Paulo
    "São Paulo",
    "Guarulhos",
    "Campinas",
    "São Bernardo do Campo",
    "Santo André",
    "Osasco",
    "Ribeirão Preto",
    "Sorocaba",
    "Mauá",
    "São José dos Campos",
    "Mogi das Cruzes",
    "Santos",
    "Diadema",
    "Jundiaí",
    "Piracicaba",
    "Bauru",
    "Itaquaquecetuba",
    "São José do Rio Preto",
    "Carapicuíba",
    "Franca",
    "Limeira",
    "Suzano",
    "Taboão da Serra",
    "Praia Grande",
    "Barueri",
    "Taubaté",
    "Americana",
    "Presidente Prudente",
    "Marília",
    "Cotia",
    "Araraquara",
    "Jacareí",
    "São Vicente",
    "Indaiatuba",
    # Rio de Janeiro
    "Rio de Janeiro",
    "São Gonçalo",
    "Duque de Caxias",
    "Nova Iguaçu",
    "Niterói",
    "Belford Roxo",
    "São João de Meriti",
    "Campos dos Goytacazes",
    "Petrópolis",
    "Volta Redonda",
    "Macaé",
    "Angra dos Reis",
    "Mesquita",
    "Magé",
    "Queimados",
    "Nova Friburgo",
    "Cabo Frio",
    "Barra Mansa",
    # Minas Gerais
    "Belo Horizonte",
    "Uberlândia",
    "Contagem",
    "Juiz de Fora",
    "Betim",
    "Montes Claros",
    "Ribeirão das Neves",
    "Uberaba",
    "Governador Valadares",
    "Ipatinga",
    "Sete Lagoas",
    "Divinópolis",
    "Santa Luzia",
    "Ibirité",
    "Poços de Caldas",
    "Patos de Minas",
    "Pouso Alegre",
    "Teófilo Otoni",
    "Barbacena",
    "Varginha",
    # Bahia
    "Salvador",
    "Feira de Santana",
    "Vitória da Conquista",
    "Camaçari",
    "Juazeiro",
    "Ilhéus",
    "Lauro de Freitas",
    "Itabuna",
    "Barreiras",
    "Jequié",
    "Alagoinhas",
    # Rio Grande do Sul
    "Porto Alegre",
    "Caxias do Sul",
    "Canoas",
    "Pelotas",
    "Santa Maria",
    "Gravataí",
    "Viamão",
    "Novo Hamburgo",
    "São Leopoldo",
    "Rio Grande",
    "Alvorada",
    "Sapucaia do Sul",
    "Cachoeirinha",
    "Passo Fundo",
    # Paraná
    "Curitiba",
    "Londrina",
    "Maringá",
    "Ponta Grossa",
    "Cascavel",
    "São José dos Pinhais",
    "Foz do Iguaçu",
    "Colombo",
    "Guarapuava",
    "Paranaguá",
    "Araucária",
    "Toledo",
    "Apucarana",
    "Campo Largo",
    # Santa Catarina
    "Florianópolis",
    "Joinville",
    "Blumenau",
    "São José",
    "Criciúma",
    "Chapecó",
    "Itajaí",
    "Jaraguá do Sul",
    "Palhoça",
    "Lages",
    # Pernambuco
    "Recife",
    "Jaboatão dos Guararapes",
    "Olinda",
    "Caruaru",
    "Petrolina",
    "Paulista",
    "Cabo de Santo Agostinho",
    "Camaragibe",
    "Garanhuns",
    # Ceará
    "Fortaleza",
    "Caucaia",
    "Juazeiro do Norte",
    "Maracanaú",
    "Sobral",
    "Crato",
    "Itapipoca",
    # Pará
    "Belém",
    "Ananindeua",
    "Santarém",
    "Marabá",
    "Parauapebas",
    "Castanhal",
    "Abaetetuba",
    # Goiás
    "Goiânia",
    "Aparecida de Goiânia",
    "Anápolis",
    "Rio Verde",
    "Luziânia",
    "Águas Lindas de Goiás",
    "Valparaíso de Goiás",
    # Maranhão
    "São Luís",
    "Imperatriz",
    "São José de Ribamar",
    "Timon",
    "Caxias",
    # Amazonas
    "Manaus",
    "Parintins",
    # Distrito Federal
    "Brasília",
    # Demais capitais
    "Maceió",
    "Macapá",
    "João Pessoa",
    "Campo Grande",
    "Cuiabá",
    "Natal",
    "Porto Velho",
    "Boa Vista",
    "Aracaju",
    "Palmas",
    "Teresina",
    "Rio Branco",
]

COORDENADAS_REGIOES = {
    "Vitória": {"lat": -20.3155, "lng": -40.3128},
    "Vila Velha": {"lat": -20.3478, "lng": -40.2949},
    "Serra": {"lat": -20.1286, "lng": -40.3078},
    "Cariacica": {"lat": -20.2632, "lng": -40.4165},
    "Viana": {"lat": -20.3903, "lng": -40.4961},
    "Guarapari": {"lat": -20.6737, "lng": -40.4990},
    "Fundão": {"lat": -19.9341, "lng": -40.4057},
    "São Paulo": {"lat": -23.5505, "lng": -46.6333},
    "Rio de Janeiro": {"lat": -22.9068, "lng": -43.1729},
    "Belo Horizonte": {"lat": -19.9167, "lng": -43.9345},
    "Salvador": {"lat": -12.9714, "lng": -38.5014},
    "Fortaleza": {"lat": -3.7172, "lng": -38.5431},
    "Manaus": {"lat": -3.1019, "lng": -60.0250},
    "Curitiba": {"lat": -25.4284, "lng": -49.2733},
    "Recife": {"lat": -8.0476, "lng": -34.8770},
    "Porto Alegre": {"lat": -30.0346, "lng": -51.2177},
    "Belém": {"lat": -1.4558, "lng": -48.4902},
    "Goiânia": {"lat": -16.6869, "lng": -49.2648},
    "Florianópolis": {"lat": -27.5954, "lng": -48.5480},
    "Maceió": {"lat": -9.6658, "lng": -35.7350},
    "Natal": {"lat": -5.7945, "lng": -35.2110},
    "Teresina": {"lat": -5.0892, "lng": -42.8019},
    "Campo Grande": {"lat": -20.4697, "lng": -54.6201},
    "João Pessoa": {"lat": -7.1195, "lng": -34.8450},
    "Aracaju": {"lat": -10.9472, "lng": -37.0731},
    "Cuiabá": {"lat": -15.6014, "lng": -56.0979},
    "Macapá": {"lat": 0.0349, "lng": -51.0694},
    "Porto Velho": {"lat": -8.7612, "lng": -63.9004},
    "Boa Vista": {"lat": 2.8235, "lng": -60.6758},
    "Palmas": {"lat": -10.2491, "lng": -48.3243},
    "Rio Branco": {"lat": -9.9754, "lng": -67.8249},
    "Brasília": {"lat": -15.7801, "lng": -47.9292},
    "São Luís": {"lat": -2.5307, "lng": -44.3068},
    "Campinas": {"lat": -22.9056, "lng": -47.0608},
    "Londrina": {"lat": -23.3045, "lng": -51.1696},
    "Joinville": {"lat": -26.3045, "lng": -48.8487},
    "Uberlândia": {"lat": -18.9186, "lng": -48.2772},
    "Feira de Santana": {"lat": -12.2664, "lng": -38.9663},
    "Juazeiro do Norte": {"lat": -7.2130, "lng": -39.3153},
    "Niterói": {"lat": -22.8832, "lng": -43.1036},
    "Ananindeua": {"lat": -1.3656, "lng": -48.3722},
    "Maringá": {"lat": -23.4206, "lng": -51.9331},
    "São Gonçalo": {"lat": -22.8268, "lng": -43.0648},
}

REGIOES_PROXIMAS = {
    "Vitória": ["Vila Velha", "Serra", "Cariacica"],
    "Vila Velha": ["Vitória", "Cariacica", "Guarapari"],
    "Serra": ["Vitória", "Cariacica", "Fundão"],
    "Cariacica": ["Vitória", "Vila Velha", "Viana"],
    "Viana": ["Cariacica", "Vila Velha", "Guarapari"],
    "Guarapari": ["Vila Velha", "Viana"],
    "Fundão": ["Serra"],
}

HABILIDADES_PREDEFINIDAS = [
    # Serviços gerais / limpeza
    "Limpeza",
    "Organização",
    "Portaria",
    "Jardinagem",
    "Manutenção predial",
    # Construção civil
    "Construção",
    "Acabamento",
    "Pintura",
    "Elétrica",
    "Hidráulica",
    "Ferramentas manuais",
    "Montagem de móveis",
    # Tecnologia / TI
    "Informática básica",
    "Excel avançado",
    "Python",
    "JavaScript",
    "SQL",
    "Git",
    "React",
    "Suporte técnico",
    "Redes",
    # Administrativo / Escritório
    "Word",
    "PowerPoint",
    "Atendimento telefônico",
    "Gestão de agenda",
    "Arquivo e documentação",
    "Digitação",
    # Comércio / Vendas
    "Vendas",
    "Negociação",
    "Caixa registradora",
    "Estoque",
    "Prospecção de clientes",
    # Transporte / Entregas
    "Direção",
    "Entregas",
    "Logística",
    "Habilitação categoria B",
    "Habilitação categoria C",
    # Alimentação / Gastronomia
    "Cozinha",
    "Confeitaria",
    "Barista",
    "Manipulação de alimentos",
    "Garçom",
    # Saúde / Bem-estar
    "Primeiros socorros",
    "Cuidados a idosos",
    "Higienização hospitalar",
    "Enfermagem básica",
    # Beleza / Estética
    "Cabeleireiro",
    "Manicure",
    "Maquiagem",
    "Depilação",
    # Comunicação / Marketing
    "Edição de vídeo",
    "Design gráfico",
    "Redes sociais",
    "Redação",
    "Fotografia",
    # Transversais
    "Pontualidade",
    "Atendimento ao cliente",
    "Trabalho em equipe",
    "Liderança",
    "Comunicação",
]

NIVEIS_EXPERIENCIA = [
    (15, "Iniciante"),
    (30, "Júnior"),
    (55, "Pleno"),
    (80, "Sênior"),
    (95, "Especialista"),
]


class FiltroCandidatoForm(FlaskForm):
    regiao = StringField("Região", validators=[Optional(), Length(max=100)])
    tipo_trabalho = SelectField(
        "Tipo de trabalho",
        choices=[("", "Todos"), *TIPOS_TRABALHO],
        validators=[Optional()],
    )
    submit = SubmitField("Filtrar")


class PerfilCandidatoForm(FlaskForm):
    regiao = StringField("Região", validators=[DataRequired(), Length(max=100)])
    categoria = SelectField(
        "Categoria de trabalho",
        choices=[("", "Selecione uma categoria...")] + CATEGORIAS_TRABALHO,
        validators=[DataRequired()],
    )
    tipo_trabalho = SelectField(
        "Tipo de trabalho desejado",
        choices=TIPOS_TRABALHO,
        validators=[DataRequired()],
    )
    disponibilidade = SelectField(
        "Disponibilidade",
        choices=DISPONIBILIDADES,
        validators=[DataRequired(), Length(max=100)],
    )
    habilidades = TextAreaField("Habilidades", validators=[DataRequired()])
    experiencia_resumida = TextAreaField(
        "Experiência resumida", validators=[Optional()]
    )
    nivel_experiencia = SelectField(
        "Nível de experiência",
        choices=NIVEIS_EXPERIENCIA,
        coerce=int,
        validators=[DataRequired(), NumberRange(min=1, max=100)],
    )
    submit = SubmitField("Salvar perfil")


class CurriculoCandidatoForm(FlaskForm):
    curriculo = FileField(
        "Currículo",
        validators=[
            FileRequired(message="Selecione um currículo para enviar."),
            FileAllowed(
                EXTENSOES_CURRICULO,
                "Envie um arquivo PDF, DOC ou DOCX.",
            ),
            FileSize(
                max_size=LIMITE_CURRICULO_BYTES,
                message="O currículo deve ter no máximo 5MB.",
            ),
        ],
    )
    submit = SubmitField("Enviar currículo")
