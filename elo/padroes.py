"""Expressões regulares do Elo: tudo o que tem forma fixa num texto sobre integração.

Responsável: Theo Haiek.

Três usos, na ordem em que acontecem:
1. anonimizar() roda ANTES de tudo sobre o texto de campo. CPF, telefone, e-mail,
   id do Salesforce e segredo viram marcadores. O diário real da integração tinha
   segredo de API em texto puro, então isso não é cuidado teórico.
2. extrair() acha as formas fixas: código HTTP, erro de plataforma, campo
   customizado, chave de registro, CPF, data, exceção, parâmetro de paginação.
3. sinais_de_categoria() traduz o achado em categoria de problema: 429 é limite
   de taxa, DUPLICATE_VALUE é duplicidade, e assim por diante.
"""
import re
from collections import Counter, namedtuple

Achado = namedtuple("Achado", "tipo valor detalhe inicio")

# 1. Código HTTP. Só com contexto antes ou frase depois: sem isso, "500 linhas"
#    viraria erro de servidor.
HTTP_CONTEXTO = re.compile(r"""
    \b(?:HTTP(?:/\d(?:\.\d)?)?|status(?:[ _]?code)?|c[oó]digo|error|erro|code)
    [\s:=#"'(]{0,3}
    (?P<codigo>[1-5]\d{2})(?!\d)
""", re.IGNORECASE | re.VERBOSE)
HTTP_FRASE = re.compile(r"""
    \b(?P<codigo>[45]\d{2})\s+
    (?:Too\s+Many\s+Requests|Unauthorized|Forbidden|Not\s+Found|Bad\s+Request
      |Internal\s+Server\s+Error|Bad\s+Gateway|Service\s+Unavailable
      |Gateway\s+Time-?out|Client\s+Error|Server\s+Error)
""", re.IGNORECASE | re.VERBOSE)

# 2. Erro de plataforma: IDENTIFICADOR_EM_CAIXA_ALTA que carrega palavra de erro.
#    STATUS_AGENDAMENTO (coluna da Moderna) também é caixa alta, mas não é erro.
#    O (?<!<) ignora o marcador <ID_SF> que o próprio anonimizador escreve.
CAIXA_ALTA = re.compile(r"(?<!<)\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+){1,6}\b")
PALAVRAS_DE_ERRO = frozenset("""
    INVALID DUPLICATE DUPLICATES DUPLICATA REQUIRED MISSING EXCEEDED UNABLE CANNOT
    DENIED FAILED FAILURE EXCEPTION ERROR EXPIRED LOCK TIMEOUT MALFORMED DISABLED
    INSUFFICIENT DELETED OUTSIDE TOO NOT UNKNOWN UNAVAILABLE UNAUTHORIZED FORBIDDEN
    DETECTED NAO SEM JA FALHA ERRO
""".split())
OAUTH = re.compile(r"\b(?:invalid_(?:grant|client|request|token|scope)|unsupported_grant_type"
                   r"|unauthorized_client|access_denied)\b")

# 3. Campo ou objeto customizado do Salesforce: sufixo __c, __r, __mdt...
CAMPO_CUSTOM = re.compile(r"\b(?:(?P<objeto>[A-Z][A-Za-z0-9]*)\.)?"
                          r"(?P<campo>[A-Za-z][A-Za-z0-9_]*?__(?:c|r|mdt|e|x|b))\b")

# 4. Id de registro do Salesforce: 15 caracteres, mais 3 de verificação no de 18.
ID_SF = re.compile(r"\b(?=[0-9A-Za-z]{0,17}\d)[0-9A-Za-z]{15}(?:[0-9A-Za-z]{3})?\b")
ALFABETO_SF = "ABCDEFGHIJKLMNOPQRSTUVWXYZ012345"

# 5. Chave externa que a integração grava em todo registro (MOD-ORC-586).
CHAVE_MOD = re.compile(r"\bMOD-(?P<tipo>PAC|AGD|ORC|ATD)-\d+(?:-\d+)*\b")

# 6. CPF com máscara, ou corrida de 9 a 11 dígitos (pode ser CPF machucado).
#    Vírgula ou ponto depois só barram se vier dígito ("12345678901,50" é valor;
#    "99999999999, e-mail" é pontuação).
CPF_MASCARA = re.compile(r"(?<![\d.])\d{3}\.\d{3}\.\d{3}-\d{2}(?![\d-])")
DIGITOS = re.compile(r"(?<![\d.,/-])\d{9,11}(?![\d/-]|[.,]\d)")

# 7. Telefone com DDD, e-mail, e valor de preenchimento. O \1 é um retrovisor:
#    "o mesmo dígito de novo", que pega 99999999999 sem listar um por um.
TELEFONE = re.compile(r"\(?\b\d{2}\)?[\s-]?9?\d{4}-\d{4}\b")
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
PREENCHIMENTO = re.compile(r"\b(\d)\1{7,10}\b|\b(?:nao|sem|naotem)@\w+\.com\b", re.IGNORECASE)

# 8. Nome com palavra repetida ("Marina Marina Duarte"). Na integração, a primeira
#    versão só achava o bloco inteiro repetido; por palavra, os casos foram de 61 a 85.
NOME_REPETIDO = re.compile(r"\b(?P<palavra>[A-ZÀ-Ý][a-zà-ÿ]+)\s+(?P=palavra)\b")

# 9. Datas nos três formatos que a mesma API da Moderna usava.
DATA = re.compile(r"""
    (?P<iso>\b\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?)?)
  | (?P<barra>\b\d{1,2}/\d{1,2}/\d{4}\b)
  | (?P<compacta>\b20\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\b)
""", re.VERBOSE)

# 10. Exceção de linguagem, como aparece em stack trace. As do simple-salesforce
#     não terminam em Error, então entram pelo nome (SalesforceLogin é função, não exceção).
EXCECAO = re.compile(r"\b(?P<nome>Salesforce(?:AuthenticationFailed|ExpiredSession|RefusedRequest"
                     r"|ResourceNotFound|MalformedRequest|MoreThanOneRecord|GeneralError)"
                     r"|[A-Z][A-Za-z0-9]*(?:Error|Exception|Timeout|Refused))\b")

# 11. Parâmetro de paginação em URL e nomes de cursor das APIs.
PAGINACAO = re.compile(r"[?&](?P<param>offset|page|per_page|pagesize|limit|cursor|after|pageToken)=[^&\s]+"
                       r"|\b(?P<cursor>nextRecordsUrl|queryMore|queryLocator|next_page_token|nextPageToken)\b",
                       re.IGNORECASE)

# 12. Segredo: o que nunca pode aparecer em slide.
SEGREDO = re.compile(r"""
    \b(?:client_secret|client_id|api[_-]?key|access_token|refresh_token|password|senha|secret)
      \s*[=:]\s*["']?[\w\-.~+/]{8,}["']?
  | \bBearer\s+[\w\-.~+/]{16,}=*
  | \beyJ[\w-]{8,}\.[\w-]{8,}\.[\w-]{8,}
  | \b[0-9a-fA-F]{32,}\b
""", re.VERBOSE)

# Categoria que cada pedaço de código de erro denuncia. A ordem importa: a
# primeira regra que casar vence.
ERRO_PARA_CATEGORIA = [
    ("SESSION", "autenticacao"), ("AUTH", "autenticacao"), ("LOGIN", "autenticacao"),
    ("ACCESS", "autenticacao"), ("LIMIT", "limite_taxa"), ("TOO_MANY", "limite_taxa"),
    ("DUPLICAT", "duplicidade"), ("CONFIAVEL", "duplicidade"), ("LOCK", "ordem"),
    ("SEM_CONTA_PAI", "ordem"), ("PARENT", "ordem"), ("FIELD", "mapeamento"),
    ("COLUMN", "mapeamento"), ("CROSS_REFERENCE", "mapeamento"), ("TYPE", "mapeamento"),
    ("TOO_LONG", "formato"), ("OUTSIDE", "formato"), ("MALFORMED", "formato"),
    ("DATE", "formato"), ("TIMEOUT", "rede"), ("UNAVAILABLE", "rede"), ("DISABLED", "ambiente"),
]
EXCECAO_PARA_CATEGORIA = [
    (re.compile(r"Authentication|Auth|Session|Login|Unauthorized|Forbidden|Permission|RefusedRequest"), "autenticacao"),
    (re.compile(r"Connection|Timeout|Refused|SSL|NameResolution|Socket|MaxRetry|Reset"), "rede"),
    (re.compile(r"JSONDecode|Unicode|Parse|Decode|Malformed"), "formato"),
]


def digitos_verificadores(nove):
    """Os dois dígitos verificadores do CPF, por módulo 11.

    Primeiro DV: pesos 10, 9, ..., 2 sobre os 9 dígitos. Segundo DV: pesos
    11, 10, ..., 2 sobre os 9 dígitos mais o primeiro DV. Em cada um, resto =
    soma mod 11; o dígito é 0 se o resto for menor que 2, senão 11 - resto.
    """
    d = [int(c) for c in nove]
    for peso_inicial in (10, 11):
        soma = sum(x * p for x, p in zip(d, range(peso_inicial, 1, -1)))
        resto = soma % 11
        d.append(0 if resto < 2 else 11 - resto)
    return f"{d[9]}{d[10]}"


def cpf_valido(onze):
    return len(onze) == 11 and onze != onze[0] * 11 and onze[9:] == digitos_verificadores(onze[:9])


def classificar_cpf(valor):
    """O que um valor de CPF é, do jeito que a integração aprendeu a ler.

    valido     11 dígitos e os dois DVs fecham
    ambiguo    fecha, termina em 0, e a rotação (0 do fim para a frente) também
               fecha: pode ser um CPF deslocado, só o cadastro de origem decide
    sem_zero   menos de 11 dígitos, mas zfill(11) fecha: o zero foi comido pela
               conversão numérica (14.313 casos recuperados na integração)
    deslocado  não fecha, mas a rotação fecha: o zero saiu da frente e entrou no fim
    invalido   nada disso
    """
    d = re.sub(r"\D", "", valor)
    rotacao = "0" + d[:-1]
    if cpf_valido(d):
        return "ambiguo" if d.endswith("0") and cpf_valido(rotacao) else "valido"
    if 9 <= len(d) < 11 and cpf_valido(d.zfill(11)):
        return "sem_zero"
    if len(d) == 11 and d.endswith("0") and cpf_valido(rotacao):
        return "deslocado"
    return "invalido"


def sufixo_id_sf(id15):
    """Os 3 caracteres que transformam o id de 15 no de 18, à prova de maiúscula/minúscula.

    Cada bloco de 5 caracteres vira um número de 5 bits: o bit i liga quando o
    i-ésimo caractere do bloco é maiúsculo. O número indexa ALFABETO_SF.
    """
    sufixo = ""
    for inicio in (0, 5, 10):
        bits = sum(1 << i for i, c in enumerate(id15[inicio:inicio + 5]) if "A" <= c <= "Z")
        sufixo += ALFABETO_SF[bits]
    return sufixo


def id_sf_valido(valor):
    if len(valor) == 18:
        return valor[15:] == sufixo_id_sf(valor[:15])
    return len(valor) == 15 and re.match(r"00[0-9A-Za-z]|01[0-9A-Za-z]|500|701|a[0-9][0-9A-Za-z]", valor) is not None


def eh_erro(identificador):
    return any(parte in PALAVRAS_DE_ERRO for parte in identificador.split("_"))


def formato_data(m):
    """iso, compacta, dd/mm, mm/dd (americana) ou ambigua (os dois componentes <= 12)."""
    if m.group("iso"):
        return "iso"
    if m.group("compacta"):
        return "compacta"
    a, b, _ = (int(x) for x in m.group("barra").split("/"))
    if a > 12:
        return "dd/mm"
    if b > 12:
        return "mm/dd"
    return "ambigua"


def extrair(texto):
    """Todas as formas fixas do texto, em ordem de aparição."""
    achados, vistos_http = [], set()

    def add(tipo, m, valor=None, detalhe="", inicio=None):
        achados.append(Achado(tipo, m.group(0) if valor is None else valor, detalhe,
                              m.start() if inicio is None else inicio))

    for rx in (HTTP_CONTEXTO, HTTP_FRASE):
        for m in rx.finditer(texto):
            if m.start("codigo") not in vistos_http:      # "HTTP 500 Internal Server Error" casa nas duas
                vistos_http.add(m.start("codigo"))
                add("http", m, m.group("codigo"), inicio=m.start("codigo"))
    for m in CAIXA_ALTA.finditer(texto):
        add("erro_plataforma" if eh_erro(m.group(0)) else "identificador", m)
    for m in OAUTH.finditer(texto):
        add("erro_oauth", m)
    for m in CAMPO_CUSTOM.finditer(texto):
        add("campo_custom", m, m.group("campo"), m.group("objeto") or "")
    for m in ID_SF.finditer(texto):
        if id_sf_valido(m.group(0)):
            add("id_sf", m, detalhe=m.group(0)[:3])
    for m in CHAVE_MOD.finditer(texto):
        add("chave_mod", m, detalhe=m.group("tipo"))
    for rx in (CPF_MASCARA, DIGITOS):
        for m in rx.finditer(texto):
            classe = classificar_cpf(m.group(0))
            if rx is CPF_MASCARA or classe != "invalido":
                add("cpf", m, detalhe=classe)
    for tipo, rx in (("telefone", TELEFONE), ("email", EMAIL), ("preenchimento", PREENCHIMENTO)):
        for m in rx.finditer(texto):
            add(tipo, m)
    for m in NOME_REPETIDO.finditer(texto):
        add("nome_repetido", m, detalhe=m.group("palavra"))
    for m in DATA.finditer(texto):
        add("data", m, detalhe=formato_data(m))
    for m in EXCECAO.finditer(texto):
        add("excecao", m, m.group("nome"))
    for m in PAGINACAO.finditer(texto):
        add("paginacao", m, m.group("param") or m.group("cursor"))
    for m in SEGREDO.finditer(texto):
        add("segredo", m, "<omitido>")
    return sorted(achados, key=lambda a: a.inicio)


# Ordem das máscaras: segredo primeiro (um client_secret em hexadecimal também
# casaria como número), e-mail antes de telefone (há dígitos dentro de e-mail).
MASCARAS = [
    ("segredo", SEGREDO, "<SEGREDO>"),
    ("email", EMAIL, "<EMAIL>"),
    ("cpf", CPF_MASCARA, "<CPF>"),
    ("telefone", TELEFONE, "<TEL>"),
    ("numero_longo", DIGITOS, "<NUM>"),
    ("nome_repetido", NOME_REPETIDO, "<NOME>"),
]


def anonimizar(texto):
    """Troca dado pessoal e segredo por marcador. Devolve (texto, contagem por tipo)."""
    contagem = Counter()
    for tipo, rx, marcador in MASCARAS:
        texto, n = rx.subn(marcador, texto)
        contagem[tipo] += n

    def troca_id(m):                      # re.sub com função: decide caso a caso
        if id_sf_valido(m.group(0)):
            contagem["id_sf"] += 1
            return "<ID_SF>"
        return m.group(0)

    texto = ID_SF.sub(troca_id, texto)
    return texto, +contagem               # o + descarta tipos com zero


def sinais_de_categoria(achados):
    """Categorias que as formas fixas denunciam sozinhas, sem precisar do spaCy."""
    categorias = set()
    for a in achados:
        if a.tipo == "http":
            codigo = int(a.valor)
            if codigo in (401, 403):
                categorias.add("autenticacao")
            elif codigo == 429:
                categorias.add("limite_taxa")
            elif codigo == 408 or codigo >= 500:
                categorias.add("rede")
        elif a.tipo == "erro_oauth":
            categorias.add("autenticacao")
        elif a.tipo == "erro_plataforma":
            categorias.update(next(([c] for pedaco, c in ERRO_PARA_CATEGORIA if pedaco in a.valor), []))
        elif a.tipo == "excecao":
            categorias.update(next(([c] for rx, c in EXCECAO_PARA_CATEGORIA if rx.search(a.valor)), []))
        elif a.tipo == "paginacao":
            categorias.add("paginacao")
        elif a.tipo == "campo_custom":
            categorias.add("mapeamento")
    return categorias


# 13. Número falado (etapa 2). Num podcast ninguém diz "429": diz "four twenty
#     nine", "five oh three" ou "four hundred and four". A regex acha a corrida de
#     números por extenso que começa em four ou five, e a conta devolve os dígitos.
#     Só vale se der um código HTTP de verdade: "five fifty" não vira 550.
UNIDADES = {p: i for i, p in enumerate("zero one two three four five six seven eight nine".split())} | {"oh": 0}
DEZ_A_DEZENOVE = {p: 10 + i for i, p in enumerate(
    "ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split())}
DEZENAS = {p: 10 * i for i, p in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split(), 2)}
PALAVRA_NUMERO = "|".join([*UNIDADES, *DEZ_A_DEZENOVE, *DEZENAS, "hundred"])
NUMERO_FALADO = re.compile(rf"\b(?:four|five)(?:[\s-]+(?:and[\s-]+)?(?:{PALAVRA_NUMERO})\b){{1,3}}", re.IGNORECASE)
CODIGOS_HTTP = {400, 401, 403, 404, 405, 408, 409, 410, 413, 415, 422, 429, 500, 501, 502, 503, 504}


def valor_falado(trecho):
    """'four twenty nine' -> 429; None se a corrida não formar um código HTTP."""
    palavras = [p for p in re.split(r"[\s-]+", trecho.lower()) if p != "and"]
    centena, resto = UNIDADES[palavras[0]] * 100, palavras[1:]
    if resto and resto[0] == "hundred":
        resto = resto[1:]
    elif resto and resto[0] in ("oh", "zero"):
        if len(resto) != 2 or resto[1] not in UNIDADES:
            return None
        resto = resto[1:]
    elif not resto or resto[0] not in {**DEZ_A_DEZENOVE, **DEZENAS}:
        return None
    if len(resto) == 2 and resto[0] in DEZENAS and resto[1] in UNIDADES:
        numero = centena + DEZENAS[resto[0]] + UNIDADES[resto[1]]
    elif len(resto) == 1:
        numero = centena + {**UNIDADES, **DEZ_A_DEZENOVE, **DEZENAS}[resto[0]]
    elif not resto:
        numero = centena
    else:
        return None
    return numero if numero in CODIGOS_HTTP else None


def normalizar_numeros_falados(texto):
    """Troca o código dito por extenso pelos dígitos. Devolve (texto, quantos trocou)."""
    trocas = 0

    def troca(m):
        nonlocal trocas
        valor = valor_falado(m.group(0))
        if valor is None:
            return m.group(0)
        trocas += 1
        return str(valor)

    return NUMERO_FALADO.sub(troca, texto), trocas
