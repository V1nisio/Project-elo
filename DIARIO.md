# Diário de bordo da etapa 1

Erros reais encontrados durante a implementação, com o conserto e o número que
provou o conserto. Todos de 06/10/2026. Cada integrante apresenta os seus.

## Flasio Vinicius (coleta e corpus de campo)

| sintoma | causa | conserto |
|---|---|---|
| A amostra ia nascer com a resposta | A primeira sondagem buscava `pagination` e `"rate limit"` no n8n | Fontes escolhidas por **sistema** (Salesforce, ERP), nunca por problema |
| O formulário falava mais que o desenvolvedor | Template da issue: `Deployment: Docker` (Airbyte), `concurrency: -1` no *Debug info* do n8n. "docker" aparecia em 124 issues | BeautifulSoup tira a seção sob título de metadados (respeitando o nível do título) e manda `<details>` para o código. Ambiente 299 → 212, ordem 101 → 61 |
| Código no meio da prosa | O GitHub renderiza permalink de código como `<table class="highlight">`, não `<pre>` | `sopa.select("pre, table.highlight")` |
| Coleta parada 51 minutos | Sem token, os comentários usam a cota *core* (60 por hora); o coletor dormiu 3.081 s esperando o reset | Teto de espera de 120 s (o mesmo do motor da integração). Acima disso, `LimiteEsgotado`: segue só com as issues e registra a lacuna no JSON |
| A API mudou durante a leitura | No ERPNext o `total_count` caiu de 379 para 378 entre a página 1 e a 2, e a página 1 veio com 99 itens | Conferência por ids únicos (300 de 300), como a integração faz com a Moderna |
| Log da coleta vazio enquanto rodava | O Python acumula a saída quando ela vai para arquivo | `sys.stdout.reconfigure(line_buffering=True)` |
| Documento sem data entrou na linha do tempo em 02/06 | Os documentos "explicados" citam datas antigas no texto | Só handoff tem data de escrita |

## Theo Haiek (expressões regulares e casos sintéticos)

| sintoma | causa | conserto |
|---|---|---|
| Segredo de API de produção em texto puro no diário | Um handoff tinha o `client_secret` num comando `curl` | `anonimizar()` roda antes de qualquer outra coisa; o texto de campo nunca sai da memória. Mascarou 6 segredos, 4 CPFs, 13 e-mails, 1 telefone e 1.624 ids do Salesforce |
| O próprio teste vazava dado | O primeiro teste de anonimização foi escrito com o começo de um segredo real e um CPF real copiados das fontes | Valores sintéticos no teste e varredura com `grep` no projeto inteiro |
| `99999999999,` não era mascarado | O lookahead de `DIGITOS` barrava qualquer vírgula depois do número | Só barra vírgula ou ponto **seguidos de dígito**: `(?![\d/-]\|[.,]\d)` |
| O anonimizador contaminava a extração | O marcador `<ID_SF>` casava como identificador em caixa alta (1.571 nos logs) | Lookbehind negativo `(?<!<)` |
| `SalesforceLogin` contado como exceção | É uma função do simple-salesforce, não exceção | Lista explícita das exceções da biblioteca |
| A saída do `extrair` no campo mostrava chaves reais de registro | Uma chave `MOD-PAC-<id>` carrega o id de um paciente no ERP: não é nome nem CPF, mas é identificador ligado a pessoa | No campo, a chave aparece só como contagem por tipo (`ORC: 41, AGD: 32, ATD: 7, PAC: 5`) |

## Belarmino Neto (spaCy e comparação)

| sintoma | causa | conserto |
|---|---|---|
| Contagem por substring enganava | Na calibração com `grep`, "pai" casou "painel" e ".env" casou "envio" | Contagem sobre tokens e lemas do spaCy |
| O lematizador do português erra | "cota" → "coto", "trava" → "trar", "conta pai" → "contar pai"; no inglês "sandboxes" → "sandboxe" | Cada termo é casado pelo lema **e** pela forma em minúsculas. No diário, 91 marcações só a forma achou |
| Lema que generaliza demais | "paging" → "page" (paginação inflou para 143), "virada" → "virar" (casava "virou"), "caiu" → "cair" (casava "cai no produto genérico") | Termos com `=` casam só pela forma exata. Paginação na comunidade 143 → 51 |
| "SEM FALHA" contado como falha | É o marcador de **sucesso** da carga noturna, e o padrão `sem + falha` o marcava como falha silenciosa | Padrão sem "falha" |
| "reconciliation" contado como divergência | No ERPNext é conciliação bancária | Fora do léxico |
| `<CPF>` virava o lema "cpf" | O tokenizador quebrava o marcador em `<`, `CPF`, `>` | Caso especial no tokenizador: o marcador é um token só |
| Uma issue dominava o ranking de termos | Um log colado dezenas de vezes na prosa ("invalid date-time") | Frequência de documento: cada termo conta uma vez por documento |

## Equipe

| sintoma | causa | conserto |
|---|---|---|
| Acento virando `�` no terminal | O console do Windows não usa UTF-8 por padrão | `sys.stdout.reconfigure(encoding="utf-8")` no início da CLI |
| spaCy não estava instalado | O Python global não tinha spaCy nem os modelos | Ambiente virtual `.venv` com Python 3.13 e modelos fixados no `requirements.txt` |
| O ensaio da demonstração ia apagar os resultados | `coletar` ao vivo sobrescreveria a coleta completa, e `analisar --limite` sobrescreveria a análise que o `comparar` lê | `--destino dados/demo.json` na coleta; análise parcial grava em `_amostra.json` |
