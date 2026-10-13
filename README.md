# Elo, etapa 1

Um analisador do que quebra entre dois sistemas que precisam conversar.

**Pergunta:** quais problemas de integração entre sistemas os desenvolvedores mais
discutem, e como eles aparecem num caso real de integração ERP × CRM rodando em
produção (ModernaNet × Salesforce)?

**Etapa 1 (texto):** processamento de linguagem natural com expressões regulares e
spaCy, sobre dados coletados pela web API do GitHub. Arquivo para o SIGAA:
`etapa1-elo.pdf`.

## Equipe e divisão

| integrante | frente | arquivos | linhas de código |
|---|---|---|---|
| Flasio Vinicius | coleta pela API do GitHub e leitura do corpus de campo | `elo/coleta.py`, `elo/campo.py` | 255 |
| Theo Haiek | expressões regulares, anonimização e casos sintéticos | `elo/padroes.py`, `elo/sintetico.py` | 254 |
| Belarmino Neto | spaCy, comparação, gráficos e relatório | `elo/analisador.py`, `elo/comparacao.py` | 213 |

Linhas contadas sem linha em branco, comentário ou docstring. O léxico das categorias
(`elo/categorias.py`) foi definido pela equipe e é mantido pelo Belarmino. A interface
`elo.py` e os testes foram escritos em conjunto: cada subcomando é do dono do módulo
que ele chama.

## Apresentação

- `apresentacao/etapa1-elo.pptx`: os 18 slides, editáveis no PowerPoint, com gráficos
  nativos e notas do apresentador (quem fala e quanto tempo, em cada slide).
- `apresentacao/etapa1-elo.pdf`: o mesmo deck em PDF, com as fontes embutidas, para o SIGAA.
- `falas_grupo/`: as falas de cada integrante, slide a slide, e o roteiro completo, para
  ensaiar (as regras proíbem ler cola na hora).

A ordem segue as regras da disciplina, e cada integrante fala cerca de 4 min 45 s:

| parte | slides | quem |
|---|---|---|
| 1. Tema, teoria, fórmulas e parâmetros | 1 a 9 | Flasio (tema e web API), Theo (regex e dígito verificador), Belarmino (spaCy e fórmulas da comparação) |
| 2. Implementação e comandos | 10 a 12 | Flasio, Theo, Belarmino, um código cada |
| 3. Diário de bordo | 13 | os três, dois erros cada |
| 4. Programa rodando e resultados | 14 a 18 | os três na demonstração; Theo nos logs; Belarmino na comparação e no fechamento |

## Instalação

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

O `requirements.txt` instala também os dois modelos do spaCy (`en_core_web_sm` e
`pt_core_news_sm`, versão 3.8.0). Testado com Python 3.13.

A coleta bruta do GitHub (`dados/comunidade.json`) não vai para o repositório, porque
traz e-mails e chaves que terceiros colaram nas issues. Depois de clonar, rode uma vez
`python elo.py coletar` (cerca de 2 minutos). As análises agregadas em `saida/` já vêm
prontas, então `python elo.py comparar` funciona direto.

## Comandos

| comando | responsável | o que faz |
|---|---|---|
| `python elo.py coletar` | Flasio | issues e comentários de 6 projetos de integração pela API REST do GitHub, com paginação pelo cabeçalho `Link`, retry, espera de limite de taxa e conferência contra o total |
| `python elo.py campo` | Flasio | lê o diário (handoffs) e os logs da integração, anonimiza e mostra só números |
| `python elo.py sintetico` | Theo | gera 17 casos sintéticos com os defeitos de formato reais da integração |
| `python elo.py extrair --corpus X` | Theo | roda as 12 expressões regulares; no sintético mostra cada achado e a linha anonimizada |
| `python elo.py analisar --corpus X` | Belarmino | spaCy: lemas, sintagmas, entidades e as 10 categorias de problema |
| `python elo.py comparar` | Belarmino | participação, diferença em pontos percentuais, ρ de Spearman, gráficos e `saida/relatorio.md` |
| `python elo.py tudo --offline` | equipe | a etapa inteira, usando a coleta já gravada |

`X` é `comunidade`, `campo` ou `sintetico`. `python elo.py --help` e
`python elo.py <comando> --help` listam todas as opções. Com a variável de ambiente
`GITHUB_TOKEN`, a coleta sobe de 10 para 30 buscas por minuto e de 60 para 5.000
pedidos por hora.

### Roteiro da demonstração

```
python elo.py --help
python elo.py coletar --max-por-fonte 20 --comentarios 0 --destino dados/demo.json
python elo.py campo
python elo.py sintetico
python elo.py extrair --corpus sintetico
python elo.py extrair --corpus campo
python elo.py analisar --corpus sintetico --doc sint-016
python elo.py analisar --corpus comunidade --limite 100
python elo.py comparar
```

`--destino dados/demo.json` preserva a coleta completa, e `--limite` grava a análise em
`saida/analise_comunidade_amostra.json`, sem substituir a completa que o `comparar` lê.

## Os três corpus

- **Comunidade:** 1.278 issues e 688 comentários de simple-salesforce, jsforce,
  Airbyte, n8n, tap-salesforce e ERPNext, em inglês (`dados/comunidade.json`, com o HTML
  bruto guardado). As fontes foram escolhidas por sistema, nunca por problema: buscar
  "pagination" faria a amostra nascer com a resposta.
- **Campo:** o diário da integração (30 handoffs datados, 90.295 palavras, 3.107 blocos)
  e os logs do motor (108 arquivos, 18.440 linhas de erro), em português. Lido no lugar,
  na pasta da integração (`--origem` ou a variável `ELO_CAMPO`), nunca copiado.
- **Sintético:** 17 casos gerados por script (`dados/sintetico.json`), sem nenhum dado
  real, para a execução ao vivo.

## Dado sensível não sai daqui

O diário real tem dado de paciente e chegou a ter credencial de API em texto puro. Por
isso:

1. `anonimizar()` roda antes de qualquer outra análise e troca segredo, e-mail, CPF,
   telefone e id do Salesforce por marcadores. No campo, mascarou 6 segredos, 4 CPFs,
   13 e-mails, 1 telefone e 1.624 ids.
2. O texto do campo só vive em memória. Para o disco vão números: contagens,
   categorias por bloco (sem texto) e termos sem nome próprio.
3. `analisar --corpus campo` nunca mostra texto, e `extrair --corpus campo` mostra
   valores só dos tipos que não são pessoais (código HTTP, código de erro, campo).
4. O `.gitignore` barra qualquer arquivo de campo que alguém grave por engano.

## Resultado

| categoria | comunidade | campo | diferença |
|---|---|---|---|
| Duplicidade e identidade | 5,6% (7º) | 19,1% (1º) | +13,6 p.p. |
| Mapeamento de campo e esquema | 15,9% (3º) | 16,4% (2º) | +0,4 p.p. |
| Ambiente e configuração | 16,3% (2º) | 15,7% (3º) | −0,6 p.p. |
| Falha silenciosa e divergência | 6,3% (6º) | 13,3% (4º) | +7,0 p.p. |
| Paginação e leitura em lotes | 3,9% (10º) | 8,8% (5º) | +4,9 p.p. |
| Autenticação e acesso | 22,0% (1º) | 8,6% (6º) | −13,4 p.p. |
| Ordem e concorrência | 5,1% (8º) | 6,4% (7º) | +1,3 p.p. |
| Formato de dado | 11,1% (4º) | 4,4% (8º) | −6,7 p.p. |
| Rede e disponibilidade | 9,5% (5º) | 4,3% (9º) | −5,2 p.p. |
| Limite de taxa e cota | 4,3% (9º) | 3,1% (10º) | −1,1 p.p. |

ρ de Spearman = 0,24. Em público, discute-se a porta de entrada (autenticação); no caso
real, o que derrubou foi identidade, falha silenciosa e paginação. Nos logs, 1.284 de
1.284 erros `REQUIRED_FIELD_MISSING` eram o mesmo campo, `RG_ou_Passapote__c`.

Limitações: é um caso só; o léxico das categorias foi feito pela equipe; os modelos do
spaCy são os pequenos e erram em texto técnico (por exemplo, marcam "Salesforce" como
lugar).

## Estrutura

```
elo.py               interface de linha de comando
elo/coleta.py        API do GitHub: paginação, limite de taxa, conferência, BeautifulSoup
elo/campo.py         diário e logs da integração, lidos no lugar e anonimizados
elo/padroes.py       as 12 expressões regulares, o dígito verificador e o anonimizador
elo/sintetico.py     casos sintéticos com os defeitos reais
elo/categorias.py    as 10 categorias e os termos em inglês e português
elo/analisador.py    pipeline do spaCy, PhraseMatcher, Matcher
elo/comparacao.py    agregação, fórmulas, gráficos e relatório
tests/               testes das expressões regulares (pytest)
dados/               coleta do GitHub e casos sintéticos
saida/               análises agregadas, gráficos e relatório
apresentacao/        os slides (.pptx) e o PDF para o SIGAA
falas_grupo/         as falas de ensaio de cada integrante e o roteiro completo
DIARIO.md            diário de bordo: os erros da implementação e os consertos
```

## Testes

```
python -m pytest tests -q
```
