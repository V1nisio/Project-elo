"""Coleta de issues e comentários de projetos de integração pela API REST do GitHub.

Responsável: Flasio Vinicius.

Três regras trazidas da integração ModernaNet x Salesforce:
1. Toda leitura é conferida contra o total que a API informa. Lá, a leitura por
   deslocamento devolvia o total certo e perdia registros. Aqui, cada fonte
   termina com: ids únicos coletados == min(total_count, máximo pedido).
2. Um 200 não confirma nada sozinho. A busca do GitHub avisa incomplete_results
   quando cortou a resposta por tempo; isso vira aviso, nunca silêncio.
3. Limite de taxa é espera, não erro. 403/429 com X-RateLimit-Remaining = 0
   dormem até X-RateLimit-Reset (ou Retry-After), como o motor faz com o 429
   da Moderna.

As fontes são escolhidas por SISTEMA (Salesforce, ERP), nunca por problema:
buscar "pagination" faria a amostra nascer com a resposta.
"""
import json
import random
import re
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from .padroes import anonimizar

API = "https://api.github.com"
POR_PAGINA = 100       # máximo que a API aceita por página
TETO_BUSCA = 1000      # a busca nunca devolve além do milésimo resultado
TETO_ESPERA = 120      # s; acima disso o limite não volta a tempo (o motor usa o mesmo teto)

FONTES = [
    ("simple-salesforce", "repo:simple-salesforce/simple-salesforce is:issue"),
    ("jsforce", "repo:jsforce/jsforce is:issue"),
    ("airbyte", "repo:airbytehq/airbyte is:issue salesforce"),
    ("n8n", "repo:n8n-io/n8n is:issue salesforce"),
    ("tap-salesforce", "repo:singer-io/tap-salesforce is:issue"),
    ("erpnext", "repo:frappe/erpnext is:issue integration"),
]


class LimiteEsgotado(RuntimeError):
    """O limite só volta depois do teto de espera: melhor parar do que travar a coleta.

    Aconteceu de verdade: sem token, os comentários usam a cota "core" (60 por
    hora), e o coletor ficou parado esperando 51 minutos pelo reset."""


class ClienteGitHub:
    """Sessão HTTP com retry, backoff exponencial e respeito ao limite de taxa."""

    def __init__(self, token=None, tentativas=4, espera_base=1.5, log=print):
        self.ses = requests.Session()
        self.ses.headers.update({
            "Accept": "application/vnd.github.full+json",   # traz body, body_text e body_html
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "elo-etapa1 (projeto de disciplina)",
        })
        if token:
            self.ses.headers["Authorization"] = f"Bearer {token}"
        self.tentativas, self.espera_base, self.log = tentativas, espera_base, log
        self.chamadas, self.restante = 0, None

    def get(self, url, params=None):
        ultimo = ""
        for tentativa in range(1, self.tentativas + 1):
            try:
                r = self.ses.get(url, params=params, timeout=30)
                self.chamadas += 1
            except requests.RequestException as e:      # rede: vale tentar de novo
                ultimo = type(e).__name__
            else:
                self.restante = r.headers.get("X-RateLimit-Remaining")
                if r.status_code == 200:
                    return r
                if r.status_code in (403, 429) and (self.restante == "0" or "Retry-After" in r.headers):
                    espera = self.espera_do_limite(r)
                    if espera > TETO_ESPERA:
                        raise LimiteEsgotado(f"limite volta em {espera / 60:.0f} min")
                    self.log(f"  limite de taxa (HTTP {r.status_code}): aguardando {espera:.0f} s")
                    time.sleep(espera)
                    continue
                if r.status_code in (401, 404, 422):     # repetir não muda a resposta
                    raise RuntimeError(f"HTTP {r.status_code}: {r.json().get('message', '')}")
                ultimo = f"HTTP {r.status_code}"
            # backoff exponencial com jitter: base * 2^(tentativa-1) * U(0,5; 1,5)
            espera = self.espera_base * 2 ** (tentativa - 1) * random.uniform(0.5, 1.5)
            self.log(f"  tentativa {tentativa} falhou ({ultimo}); nova em {espera:.1f} s")
            time.sleep(espera)
        raise RuntimeError(f"{url}: {self.tentativas} tentativas falharam; última: {ultimo}")

    @staticmethod
    def espera_do_limite(r):
        if "Retry-After" in r.headers:
            return float(r.headers["Retry-After"]) + 1
        reset = float(r.headers.get("X-RateLimit-Reset", time.time() + 60))
        return max(reset - time.time(), 1) + 1

    def buscar(self, consulta, maximo):
        """Busca paginada pelo cabeçalho Link. Devolve (itens, conferência)."""
        url = f"{API}/search/issues"
        params = {"q": consulta, "per_page": min(POR_PAGINA, maximo), "sort": "comments", "order": "desc"}
        itens, total, incompleto, pagina = [], 0, False, 0
        while url and len(itens) < maximo:
            r = self.get(url, params)
            corpo = r.json()
            pagina += 1
            total = corpo["total_count"]
            incompleto = incompleto or corpo["incomplete_results"]
            itens += corpo["items"]
            self.log(f"  página {pagina}: +{len(corpo['items'])} itens "
                     f"(total na API {total}; restam {self.restante} chamadas)")
            url = r.links.get("next", {}).get("url")    # o requests já interpreta o Link
            params = None                                # a URL do next já carrega a consulta
        itens = itens[:maximo]
        esperado = min(total, maximo, TETO_BUSCA)
        unicos = len({i["id"] for i in itens})
        return itens, {"total_api": total, "esperado": esperado, "coletados": len(itens),
                       "unicos": unicos, "incompleto": incompleto,
                       "fecha": unicos == esperado and not incompleto}

    def comentarios(self, url, maximo=50):
        return self.get(url, {"per_page": min(maximo, POR_PAGINA)}).json()


TITULOS = ["h1", "h2", "h3", "h4", "h5", "h6"]
# Seções de formulário que descrevem a máquina, não o problema: "Deployment: Docker"
# em centenas de issues do Airbyte inflava a categoria ambiente.
METADADOS = re.compile(r"^\s*(environment|debug info|versions?|installation method|deployment"
                       r"|operating system|os|hosting|database|severity|module|system info)\b", re.IGNORECASE)


def separar_prosa_e_codigo(html):
    """BeautifulSoup sobre o body_html: o que é código vai para as regex, a fala de
    quem escreveu vai para o spaCy, e o formulário do template sai.

    <pre>, permalink de código (table.highlight) e <details> (log, debug info) são
    código. Seção sob título de metadados ("Environment", "Debug Info") sai inteira.
    Os títulos também saem: numa issue, eles são o formulário ("Describe the bug").
    """
    sopa = BeautifulSoup(html or "", "html.parser")
    codigo = []
    for bloco in sopa.select("details, pre, table.highlight"):
        if not bloco.decomposed:                        # pode já ter saído dentro de um <details>
            codigo.append(bloco.get_text("\n"))
            bloco.decompose()
    for titulo in sopa.find_all(TITULOS):
        if titulo.decomposed or not METADADOS.match(titulo.get_text()):
            continue
        nivel = int(titulo.name[1])                     # a seção vai até o próximo título de nível <= este
        irmao = titulo.find_next_sibling()
        while irmao is not None and not (irmao.name in TITULOS and int(irmao.name[1]) <= nivel):
            seguinte = irmao.find_next_sibling()
            irmao.decompose()
            irmao = seguinte
    for marca in sopa.find_all(["img", "svg", *TITULOS]):
        marca.decompose()
    return sopa.get_text(" ", strip=True), "\n".join(codigo)


def documento(fonte, item, comentarios=()):
    """Uma issue (com os comentários lidos) vira um documento do corpus. O HTML
    bruto fica guardado: se a regra de limpeza mudar, não é preciso coletar de novo."""
    doc = {
        "fonte": fonte, "id": f"gh-{item['id']}", "numero": item["number"],
        "titulo": item["title"], "url": item["html_url"], "data": item["created_at"][:10],
        "estado": item["state"], "rotulos": [r["name"] for r in item.get("labels", [])],
        "n_comentarios": item.get("comments", 0), "comentarios_lidos": len(comentarios),
        "html": [item.get("body_html"), *(c.get("body_html") for c in comentarios)],
    }
    return {**doc, **derivar(doc)}


def derivar(doc):
    """prosa e codigo a partir do HTML guardado, já anonimizados: issue pública
    também traz e-mail pessoal e segredo colado em JSON de workflow."""
    prosas, codigos = [doc["titulo"] + "."], []
    for html in doc["html"]:
        prosa, codigo = separar_prosa_e_codigo(html)
        prosas.append(prosa)
        codigos.append(codigo)
    prosa, mascaras = anonimizar(" ".join(p for p in prosas if p))
    codigo, mascaras_codigo = anonimizar("\n".join(c for c in codigos if c))
    return {"prosa": prosa, "codigo": codigo, "mascaras": dict(mascaras + mascaras_codigo)}


def coletar(destino, maximo_por_fonte=300, comentarios_por_fonte=5, token=None, fontes=FONTES, log=print):
    """Coleta todas as fontes, confere cada uma e grava o corpus em JSON."""
    cliente = ClienteGitHub(token=token, log=log)
    documentos, conferencias, lacuna = [], {}, None
    for nome, consulta in fontes:
        log(f"[{nome}] {consulta}")
        itens, conferencia = cliente.buscar(consulta, maximo_por_fonte)
        conferencias[nome] = conferencia
        log(f"[{nome}] conferência: {conferencia['unicos']} únicos de {conferencia['esperado']} esperados"
            f"{', RESPOSTA INCOMPLETA' if conferencia['incompleto'] else ''} -> "
            f"{'fecha' if conferencia['fecha'] else 'NÃO FECHA'}")
        vistos = set()
        for posicao, item in enumerate(itens):
            if item["id"] in vistos:                     # página repetida não vira documento repetido
                continue
            vistos.add(item["id"])
            lidos = []
            if posicao < comentarios_por_fonte and item.get("comments") and not lacuna:
                try:
                    lidos = cliente.comentarios(item["comments_url"])
                except LimiteEsgotado as e:          # degrada: segue só com as issues e registra
                    lacuna = f"comentários interrompidos em {nome}: {e}"
                    log(f"  {lacuna}; seguindo só com as issues")
            documentos.append(documento(nome, item, lidos))
    pacote = {"coletado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "chamadas": cliente.chamadas, "lacuna": lacuna, "conferencias": conferencias,
              "documentos": documentos}
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(pacote, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"{len(documentos)} documentos gravados em {destino.name} ({cliente.chamadas} chamadas à API)")
    return pacote


def carregar(caminho, limite=None):
    """Lê a coleta gravada e refaz prosa e código com a regra de limpeza atual."""
    pacote = json.loads(caminho.read_text(encoding="utf-8"))
    pacote["documentos"] = pacote["documentos"][:limite]
    for doc in pacote["documentos"]:
        if "html" in doc:
            doc.update(derivar(doc))
    return pacote
