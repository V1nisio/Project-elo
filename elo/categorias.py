"""As dez categorias de problema de integração e os termos que as denunciam.

Mantido por: Belarmino Neto (definido em conjunto pela equipe).

A categoria é a língua comum entre um corpus em inglês (GitHub) e um em
português (o diário da integração): termos não se comparam entre línguas,
categorias sim. Cada termo é casado duas vezes pelo analisador: pelo lema
(pega "duplicadas" a partir de "duplicado") e pela forma em minúsculas (pega
o que o lematizador erra, como "cota" virando "coto").

Termo com "=" na frente só casa pela forma exata, porque o lema dele
generaliza demais: "paging" vira "page", "ignored" vira "ignore", "virada"
vira "virar" (que casaria com "virou"), "caiu" vira "cair".

Ficaram de fora, de propósito, palavras que casariam por acaso: "page" (página
web), "merge" (merge de pull request), "connection" (no Airbyte é configuração),
"version" e "install" (todo bug report tem), "campo" e "field" sozinhos,
"reconciliation" (no ERPNext é conciliação bancária).
"""

CATEGORIAS = {
    "autenticacao": {
        "rotulo": "Autenticação e acesso",
        "en": ["authentication", "authenticate", "auth", "oauth", "oauth2", "token", "access token",
               "refresh token", "bearer token", "security token", "session id", "session expired",
               "expired session", "invalid session", "credential", "credentials", "login", "log in",
               "unauthorized", "unauthenticated", "forbidden", "jwt", "client secret", "client id",
               "client credentials", "connected app", "api key", "password", "permission", "permissions",
               "authorization", "consumer key", "consumer secret", "grant type", "sso", "saml"],
        "pt": ["autenticação", "autenticar", "token", "credencial", "credenciais", "segredo", "senha",
               "login", "client credentials", "jwt", "sessão expirada", "não autorizado", "acesso negado",
               "permissão", "permissões", "usuário de integração", "connected app", "oauth"],
    },
    "limite_taxa": {
        "rotulo": "Limite de taxa e cota",
        "en": ["rate limit", "rate limits", "rate limiting", "rate-limit", "ratelimit", "throttle",
               "throttling", "throttled", "quota", "api limit", "api limits", "request limit",
               "limit exceeded", "too many requests", "concurrent requests", "concurrency limit",
               "daily limit", "api calls", "api usage", "governor limit", "governor limits", "requests per"],
        "pt": ["limite de requisições", "limite de requisição", "limite de taxa", "cota", "cotas",
               "chamadas de api", "chamada de api", "muitas requisições", "requisições simultâneas",
               "pedidos ao mesmo tempo", "vazão", "teto de fluxos", "estourar a cota", "consumo de api"],
    },
    "paginacao": {
        "rotulo": "Paginação e leitura em lotes",
        "en": ["pagination", "paginate", "paginated", "=paging", "next page", "page size", "pagesize",
               "offset", "cursor", "nextrecordsurl", "next records url", "querymore", "query more",
               "query_all", "query all", "querylocator", "batch size", "chunk size", "pk chunking",
               "first page", "last page", "page token"],
        "pt": ["paginação", "página", "páginas", "offset", "deslocamento", "cursor", "partição",
               "partições", "fatia", "fatias", "varredura", "leitura por calendário", "por calendário",
               "página embaralhada", "páginas embaralhadas", "embaralhar", "tamanho da página"],
    },
    "duplicidade": {
        "rotulo": "Duplicidade e identidade",
        "en": ["duplicate", "duplicates", "duplicated", "duplication", "dedup", "dedupe", "deduplicate",
               "deduplication", "upsert", "upserting", "external id", "externalid", "unique",
               "uniqueness", "merge records", "merge accounts", "merge contacts", "matching rule",
               "duplicate rule", "idempotent", "idempotency", "primary key", "wrong record", "wrong account"],
        "pt": ["duplicata", "duplicatas", "duplicidade", "duplicado", "duplicada", "duplicados",
               "duplicadas", "duplicar", "mesclagem", "mesclar", "upsert", "chave externa",
               "código externo", "external id", "identidade", "homônimo", "homônimos", "idempotente",
               "código único", "conta duplicada", "religar", "religados", "pessoa errada",
               "paciente errado", "paciente errada", "conta errada"],
    },
    "mapeamento": {
        "rotulo": "Mapeamento de campo e esquema",
        "en": ["field mapping", "mapping", "map fields", "custom field", "custom fields", "custom object",
               "schema", "picklist", "pick list", "required field", "required fields", "missing field",
               "field type", "data type", "field level security", "field-level security", "fls",
               "metadata", "column", "columns", "sobject", "lookup field", "relationship field",
               "record type", "recordtype", "invalid field", "no such column", "field name", "field names"],
        "pt": ["de/para", "depara", "mapeamento", "mapear", "campo obrigatório", "campos obrigatórios",
               "campo customizado", "campos customizados", "picklist", "lista de seleção", "esquema",
               "coluna", "colunas", "fls", "permissão de campo", "nome de coluna", "tipo de registro",
               "produto genérico", "campo vazio", "campos vazios", "sem origem", "nome do campo"],
    },
    "formato": {
        "rotulo": "Formato de dado",
        "en": ["date format", "datetime", "date time", "timezone", "time zone", "utc", "encoding",
               "utf-8", "utf8", "unicode", "decimal", "locale", "parse error", "parsing", "format",
               "formatting", "truncated", "truncate", "leading zero", "leading zeros", "null value",
               "empty string", "string too long", "invalid date", "iso 8601", "serialization",
               "deserialization", "special characters", "number format", "precision", "rounding",
               "daylight saving"],
        "pt": ["formato", "formatos", "formato de data", "fuso", "fuso horário", "utc", "codificação",
               "acentuação", "zero à esquerda", "zeros à esquerda", "máscara", "truncado", "truncada",
               "truncar", "decimal", "casas decimais", "normalização", "normalizar", "dígito verificador",
               "data americana", "três formatos", "conversão numérica", "tipo numérico"],
    },
    "ordem": {
        "rotulo": "Ordem e concorrência",
        "en": ["race condition", "race conditions", "concurrency", "concurrent", "parallel", "in parallel",
               "lock", "locked", "locking", "deadlock", "unable to lock", "order of execution",
               "execution order", "out of order", "sequence", "sequential", "parent record", "child record",
               "parent account", "parent object", "queue", "simultaneous", "at the same time",
               "webhook", "webhooks", "trigger order"],
        "pt": ["ordem de execução", "fora de ordem", "concorrência", "concorrente", "simultâneo",
               "simultâneos", "em paralelo", "paralelo", "trava", "travas", "lock", "conta pai",
               "registro pai", "sem conta pai", "fila", "webhook", "duas máquinas", "ao mesmo tempo",
               "uma rodada por vez"],
    },
    "silenciosa": {
        "rotulo": "Falha silenciosa e divergência",
        "en": ["silently", "silent", "no error", "without error", "without any error", "data loss",
               "lost data", "missing data", "missing records", "lost records", "not synced", "out of sync",
               "inconsistent", "inconsistency", "discrepancy", "mismatch", "partially", "incomplete",
               "wrong data", "incorrect data", "not saved", "not updated", "=ignored", "=swallowed", "no effect",
               "nothing happens"],
        "pt": ["em silêncio", "silencioso", "silenciosa", "silenciosamente", "sem erro", "sem aviso",
               "perda", "perdido", "perdidos", "perder", "sumir", "sumiu", "inconsistente", "divergência",
               "divergências", "divergente", "não confirmado", "não confirmou",
               "fora da leitura", "ignorado", "ignorada", "incompleto", "incompleta", "sem efeito",
               "não chegou"],
    },
    "rede": {
        "rotulo": "Rede e disponibilidade",
        "en": ["timeout", "timeouts", "time out", "timed out", "connection reset", "connection refused",
               "connection error", "connection timeout", "connection closed", "lost connection", "network",
               "dns", "ssl", "tls", "certificate", "proxy", "socket", "econnreset", "etimedout",
               "econnrefused", "server error", "internal server error", "bad gateway", "service unavailable",
               "unavailable", "outage", "downtime", "retry", "retries", "retrying", "backoff",
               "unreachable", "hang", "hangs"],
        "pt": ["timeout", "tempo esgotado", "conexão", "rede", "fora do ar", "indisponível",
               "instabilidade", "erro do servidor", "nova tentativa", "novas tentativas", "retentativa",
               "retry", "queda", "=caiu", "lentidão", "lento", "backoff", "dns", "ssl", "certificado", "proxy"],
    },
    "ambiente": {
        "rotulo": "Ambiente e configuração",
        "en": ["sandbox", "sandboxes", "production", "staging", "test environment", "environment",
               "environment variable", "environment variables", "env var", "configuration", "config",
               "api version", "deprecated", "deprecation", "instance url", "login url",
               "test.salesforce.com", "my domain", "self-hosted", "self hosted", "docker", "proxy settings"],
        "pt": ["homologação", "produção", "ambiente", "ambiente de teste", "sandbox", "configuração",
               "variável de ambiente", "versão da api", "=virada", "virada para produção", "máquina dona",
               "servidor", "instância", "cópia congelada", "base de teste"],
    },
}

# Construções que o PhraseMatcher não pega, porque dependem de negação ou de
# um número no meio. Padrões de token do Matcher do spaCy.
PADROES_TOKEN = {
    "en": {
        "silenciosa": [
            [{"LOWER": {"IN": ["no", "without"]}}, {"LOWER": "any", "OP": "?"},
             {"LEMMA": {"IN": ["error", "exception", "warning", "message"]}}],
            [{"LEMMA": {"IN": ["return", "respond", "succeed", "report"]}},
             {"LOWER": {"IN": ["200", "success", "successfully", "ok", "true"]}}],
            [{"LOWER": "but"}, {"LOWER": "nothing"}, {"LEMMA": {"IN": ["happen", "change", "show", "appear"]}}],
        ],
        "duplicidade": [
            [{"LEMMA": {"IN": ["create", "insert", "sync", "run", "send"]}}, {"OP": "?"}, {"LOWER": "twice"}],
        ],
        "rede": [[{"LEMMA": "time"}, {"LOWER": "out"}]],
    },
    "pt": {
        "silenciosa": [
            [{"LOWER": "sem"}, {"LEMMA": {"IN": ["erro", "aviso", "alerta"]}}],   # "SEM FALHA" é o sucesso da carga
            [{"LOWER": {"IN": ["não", "nao", "nunca"]}},
             {"LEMMA": {"IN": ["confirmar", "chegar", "aparecer", "fechar", "bater", "gravar"]}}],
            [{"LEMMA": {"IN": ["devolver", "retornar", "responder"]}}, {"LOWER": "200"}],
        ],
        "duplicidade": [
            [{"LEMMA": {"IN": ["criar", "gravar", "ligar", "adotar"]}}, {"OP": "?"},
             {"LOWER": {"IN": ["duas", "dois"]}}, {"LEMMA": {"IN": ["vez", "cópia", "conta"]}}],
        ],
    },
}

ORDEM = list(CATEGORIAS)
ROTULOS = {chave: info["rotulo"] for chave, info in CATEGORIAS.items()}
