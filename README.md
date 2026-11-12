# TrampoMatch

Plataforma web que conecta candidatos a oportunidades locais por meio de compatibilidade ponderada e interesse mútuo. A conexão é aberta quando candidato e contratante demonstram interesse na mesma vaga.

Projeto final da disciplina Programação Web Avançada da Universidade Vila Velha, desenvolvido em 2026 por Gabriel Aguiar, Arthur Prates Pessoti e Leonardo Rosa dos Santos, sob orientação do professor Wanderson Muniz de Santana.

## Funcionalidades

- Perfis distintos para candidatos e contratantes.
- Cadastro, busca e gerenciamento de vagas.
- Compatibilidade baseada em habilidades, região, tipo de vaga, experiência e disponibilidade.
- Interesse mútuo antes da abertura do contato.
- Convites, recusas, descartes e histórico de matches.
- Upload de currículo com validação de tipo e tamanho.
- Autenticação tradicional e OAuth Google opcional.

## Algoritmo de compatibilidade

O score considera seis critérios. Habilidades representam 80% da pontuação; região, tipo de vaga, experiência e disponibilidade representam 5% cada. O sistema também aplica:

- Normalização de sinônimos de habilidades.
- Correspondência aproximada com RapidFuzz.
- Clusters de cidades da Grande Vitória.
- Critérios eliminatórios para região e turno incompatíveis.
- Limiar de 70% para classificar uma oportunidade como compatível.

## Tecnologias

- Python 3.12 e Flask 3.
- SQLAlchemy, Flask-Login e Flask-WTF.
- Jinja2, Bulma e CSS customizado.
- RapidFuzz para comparação de habilidades.
- Pytest com banco SQLite em memória.

## Interface

![Dashboard do TrampoMatch](trampomatch/static/img/hero-dashboard.png)

![Onboarding de contratante](trampomatch/static/img/hero-contratante-onboarding.png)

## Executar localmente

```bash
python -m venv .venv
pip install -e ".[dev,test]"
```

Copie `.env.example` para `.env.dev`, substitua a chave de desenvolvimento e configure o OAuth somente se quiser usar login com Google.

```bash
flask --app app run --debug
```

## Testes e qualidade

```bash
pytest -q
flake8 trampomatch tests
```

A versão publicada foi validada com 75 testes automatizados.

## Status

O projeto foi aprovado na apresentação acadêmica e apresentado à liderança de RH da UVV para avaliação como possível solução. A apresentação não representa adoção institucional.
