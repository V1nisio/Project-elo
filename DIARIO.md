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

# Diário de bordo da etapa 2 (áudio)

Erros reais da sondagem dos feeds e da implementação, de 12/11/2026.

## Flasio Vinicius (coleta dos podcasts)

| sintoma | causa | conserto |
|---|---|---|
| 111 episódios num podcast só | O filtro lia a descrição, e o anúncio de patrocínio cita ferramenta (Airbyte, dlt) em quase todo episódio | Filtro só no título: 6 episódios |
| O Ryan Singer entrou no corpus | `\bsinger\b` casou o autor do Basecamp, no SE Radio | "Singer" só vale seguido de SDK ou tap |
| "Continuous Integration" entrou como integração | É CI/CD, outro assunto (SE Radio 498 e 133) | Lookbehind negativo: `(?<!continuous )\bintegrations?\b` |
| A busca por "Frappe" achou um podcast indonésio sobre alfândega | A API de busca da Apple casa por palavra solta | Podcast escolhido pelo nome exato; feed conhecido como reserva (o Data Engineering Podcast não volta pelo nome) |
| O notebook desligou sem bateria no meio da instalação | 4% de bateria, fora da tomada | Download em `.part` com cabeçalho `Range`; manifesto gravado num temporário e trocado a cada episódio. Coleta refeita: 20 de 20 conferem |

## Theo Haiek (sinal, sintético falado e números falados)

| sintoma | causa | conserto |
|---|---|---|
| Com ruído, 0 de 9 pausas achadas | O limiar de silêncio é relativo ao pico (−35 dB); chiado a 10 dB da fala fica acima dele, e a fala vira 100% | Limitação registrada: o cruzamento por zero denuncia o áudio sujo (0,353 contra 0,118 no limpo) |
| "Pausa antes" com mediana 0 s nos dois grupos | Em 53% dos 12.213 trechos, o Whisper cola o início no fim do anterior (também no tempo por palavra) | `silencio_antes()`: a pausa é o silêncio medido no sinal (abaixo de −35 dB) que termina até 0,4 s do início do trecho. Mediana de 0,13 s num episódio; teste `test_pausa_antes_vem_do_sinal_e_nao_do_whisper` |
| A regex dos números falados não tinha o que trocar | Na voz limpa, o Whisper já escreve "error 429" em dígitos | Teste da regex isolado (`test_numero_falado_vira_codigo_http`). Nos 20 episódios reais também foram 0 trocas: ela fica como rede de segurança |
| "five oh three" não virava código HTTP | A regex de HTTP da etapa 1 exige uma palavra de contexto (error, status, code) antes do número | Frases do sintético com "with error ..."; "five fifty users" continua fora porque só código HTTP real é trocado |
| A voz do Windows sai a 22.050 Hz e com silêncio nas pontas | Formato do SAPI | `librosa.resample` para 16 kHz e `effects.trim` antes de inserir as pausas do gabarito |

## Belarmino Neto (transcrição e comparação)

| sintoma | causa | conserto |
|---|---|---|
| O small levaria 6 h para o corpus | 2,3x o tempo real na CPU, sem placa de vídeo | Medido em 60 s reais: tiny 11,2x, base 6,4x, small 2,3x, com o mesmo texto no trecho. Escolhido o base |
| "upsert" virou "absurd" e "sync" virou "sink" | O jargão de integração é raro no treino do Whisper | WER registrado (6,6% no tiny, voz limpa); a categoria ainda é achada em 10 de 10 frases |
| Clipping e ruído pioram a transcrição; estéreo e volume baixo não | A carga converte para mono 16 kHz, e o modelo é robusto a volume | WER por versão no `transcrever --corpus sintetico-falado`: 6,6% limpo, 9,0% clipping, 9,6% ruído |
