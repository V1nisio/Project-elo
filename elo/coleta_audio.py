"""Coleta de podcasts sobre integração: a API de busca da Apple, o RSS e o MP3.

Responsável: Flasio Vinicius.

As mesmas três regras da coleta do GitHub (coleta.py), agora para áudio:
1. Fonte por SISTEMA, nunca por problema. Um episódio entra se o título cita um
   dos sistemas (Salesforce, Airbyte, n8n, ERP...); "integration" só completa as
   vagas. Buscar "rate limit" faria a amostra nascer com a resposta.
2. Todo download é conferido: o tamanho contra o que o RSS declara e a duração
   decodificada contra a itunes:duration. Um arquivo que baixou "até o fim" mas
   veio cortado não passa calado.
3. Queda de rede não perde trabalho. O MP3 baixa num .part, e a retomada pede só
   o que falta pelo cabeçalho Range. O manifesto é regravado a cada episódio.

O áudio fica em dados/audio/ (fora do git: direito autoral e 800 MB). Para o
repositório vai só o manifesto, com metadados públicos.
"""
import hashlib
import json
import random
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

BUSCA_APPLE = "https://itunes.apple.com/search"
ITUNES = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
TAXA = 16_000            # Hz: o que o Whisper espera, e Nyquist dá voz até 8 kHz
TOLERANCIA = 0.02        # 2% de diferença entre a duração declarada e a medida

# (código, nome exato do podcast na Apple, feed conhecido se a busca falhar)
FONTES = [
    ("salesforce", "Salesforce Developer Podcast", "https://a.sfdcstatic.com/developer-website/podcast/rss.xml"),
    ("dataeng", "Data Engineering Podcast", "https://serve.podhome.fm/rss/1c0357c0-6aba-5766-a2d5-2090d8dab6bc"),
    ("n8n", "The n8n Masterclass", "https://rss.buzzsprout.com/2545272.rss"),
    ("seradio", "Software Engineering Radio - the podcast for professional software developers",
     "https://rss.libsyn.com/shows/21070/destinations/23379.xml"),
]

# "Singer" sozinho pegou o Ryan Singer, do Basecamp; só vale junto de SDK, tap ou Meltano.
SISTEMA = re.compile(r"\b(?:salesforce|mulesoft|airbyte|n8n|meltano|dlt|erp|erpnext|frappe"
                     r"|singer\s+(?:sdk|tap))\b", re.IGNORECASE)
# "Continuous Integration" é CI/CD, outro assunto.
INTEGRACAO = re.compile(r"(?<!continuous )\bintegrations?\b", re.IGNORECASE)


def segundos(texto):
    """itunes:duration vem como "3245", "54:05" ou "1:02:30"."""
    total = 0
    for parte in (texto or "0").strip().split(":"):
        total = total * 60 + int(float(parte))
    return total


def pedir(sessao, url, tentativas=4, log=print, **kw):
    """GET com retry e backoff exponencial com jitter, como o ClienteGitHub."""
    for tentativa in range(1, tentativas + 1):
        try:
            r = sessao.get(url, timeout=60, **kw)
            if r.status_code in (200, 206):
                return r
            ultimo = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            ultimo = type(e).__name__
        espera = 1.5 * 2 ** (tentativa - 1) * random.uniform(0.5, 1.5)
        log(f"  tentativa {tentativa} falhou ({ultimo}); nova em {espera:.1f} s")
        time.sleep(espera)
    raise RuntimeError(f"{url}: {tentativas} tentativas falharam")


def achar_feed(sessao, nome, reserva, log=print):
    """A API de busca da Apple devolve o feedUrl do podcast pelo nome."""
    try:
        r = pedir(sessao, BUSCA_APPLE, params={"term": nome, "entity": "podcast", "limit": 10}, log=log)
        for p in r.json()["results"]:
            if p["collectionName"].lower() == nome.lower() and p.get("feedUrl"):
                return p["feedUrl"]
    except (RuntimeError, ValueError, KeyError):
        pass
    log(f"  a busca não achou '{nome}'; usando o feed conhecido")
    return reserva


def episodios(xml, codigo):
    """Os itens do RSS que têm MP3, do mais novo para o mais antigo."""
    canal = ET.fromstring(xml).find("channel")
    saida = []
    for item in canal.findall("item"):
        anexo = item.find("enclosure")
        if anexo is None or "audio" not in (anexo.get("type") or "audio"):
            continue
        guid = item.findtext("guid") or anexo.get("url")
        data = item.findtext("pubDate")
        saida.append({
            "id": f"{codigo}-{hashlib.sha1(guid.encode()).hexdigest()[:6]}",
            "fonte": codigo, "titulo": " ".join((item.findtext("title") or "").split()),
            "data": parsedate_to_datetime(data).date().isoformat() if data else None,
            "url": anexo.get("url"), "bytes_rss": int(anexo.get("length") or 0),
            "duracao_rss": segundos(item.findtext(ITUNES + "duration")),
        })
    return sorted(saida, key=lambda e: e["data"] or "", reverse=True), canal.findtext("copyright") or ""


def selecionar(lista, maximo):
    """Primeiro quem cita um sistema pelo nome; "integration" só completa as vagas."""
    por_sistema = [e for e in lista if SISTEMA.search(e["titulo"])]
    por_integracao = [e for e in lista if INTEGRACAO.search(e["titulo"]) and e not in por_sistema]
    return (por_sistema + por_integracao)[:maximo]


def baixar(sessao, ep, pasta, log=print):
    """Baixa em partes; se já existe um .part, pede só o que falta (Range)."""
    final = pasta / f"{ep['id']}.mp3"
    if final.exists():
        return final
    parcial = final.with_suffix(".mp3.part")
    ja = parcial.stat().st_size if parcial.exists() else 0
    cabecalho = {"Range": f"bytes={ja}-"} if ja else {}
    r = pedir(sessao, ep["url"], headers=cabecalho, stream=True, log=log)
    if ja and r.status_code != 206:          # o servidor ignorou o Range: recomeça do zero
        ja = 0
    with open(parcial, "ab" if ja else "wb") as f:
        for bloco in r.iter_content(1 << 16):
            f.write(bloco)
    parcial.replace(final)
    return final


def duracao_medida(caminho):
    import av                                 # vem com o faster-whisper e já traz o ffmpeg
    with av.open(str(caminho)) as c:
        return c.duration / 1_000_000


def conferir(ep, caminho):
    """Tamanho contra o RSS e duração decodificada contra a declarada."""
    ep["bytes"] = caminho.stat().st_size
    ep["duracao"] = round(duracao_medida(caminho), 1)
    ok_bytes = not ep["bytes_rss"] or abs(ep["bytes"] - ep["bytes_rss"]) <= TOLERANCIA * ep["bytes_rss"]
    ok_dur = not ep["duracao_rss"] or abs(ep["duracao"] - ep["duracao_rss"]) <= max(30, TOLERANCIA * ep["duracao_rss"])
    ep["confere"] = bool(ok_bytes and ok_dur)
    return ep["confere"]


def gravar(destino, pacote):
    """Grava num temporário e troca: um desligamento no meio não corrompe o manifesto."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(".tmp")
    tmp.write_text(json.dumps(pacote, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(destino)


def coletar(destino, pasta_audio, maximo_por_fonte=6, so_listar=False, offline=False, log=print):
    sessao = requests.Session()
    sessao.headers["User-Agent"] = "elo-etapa2 (projeto de disciplina)"
    pasta_feeds = pasta_audio / "feeds"
    pasta_feeds.mkdir(parents=True, exist_ok=True)
    pacote = {"coletado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"), "fontes": {}, "episodios": []}
    for codigo, nome, reserva in FONTES:
        copia = pasta_feeds / f"{codigo}.xml"
        if offline and copia.exists():
            xml, url = copia.read_bytes(), "(cópia local)"
        else:
            url = achar_feed(sessao, nome, reserva, log)
            xml = pedir(sessao, url, log=log).content
            copia.write_bytes(xml)            # a cópia permite listar sem internet (--offline)
        lista, direitos = episodios(xml, codigo)
        escolhidos = selecionar(lista, maximo_por_fonte)
        pacote["fontes"][codigo] = {"nome": nome, "feed": url, "itens_no_feed": len(lista),
                                    "escolhidos": len(escolhidos), "direitos": direitos[:120]}
        log(f"[{codigo}] {nome}: {len(lista)} episódios no feed, {len(escolhidos)} escolhidos por sistema")
        for ep in escolhidos:
            log(f"    {ep['data']}  {ep['duracao_rss'] // 60:3d} min  {ep['titulo'][:80]}")
        pacote["episodios"] += escolhidos
    gravar(destino, pacote)
    if so_listar:
        return pacote
    pasta_audio.mkdir(parents=True, exist_ok=True)
    for i, ep in enumerate(pacote["episodios"], 1):
        log(f"[{i}/{len(pacote['episodios'])}] {ep['id']}: baixando")
        caminho = baixar(sessao, ep, pasta_audio, log)
        conferir(ep, caminho)
        log(f"    {ep['bytes'] / 1e6:.1f} MB, {ep['duracao'] / 60:.1f} min -> {'confere' if ep['confere'] else 'NÃO CONFERE'}")
        gravar(destino, pacote)               # a cada episódio: nada se perde se cair
    return pacote


def reconferir(destino, pasta_audio, log=print):
    """Confere o que já foi baixado, sem internet."""
    pacote = json.loads(destino.read_text(encoding="utf-8"))
    for ep in pacote["episodios"]:
        caminho = pasta_audio / f"{ep['id']}.mp3"
        if not caminho.exists():
            ep["confere"] = False
            log(f"  {ep['id']}: FALTA o arquivo")
            continue
        conferir(ep, caminho)
        log(f"  {ep['id']}: {ep['bytes'] / 1e6:6.1f} MB  {ep['duracao'] / 60:5.1f} min "
            f"(RSS {ep['duracao_rss'] / 60:5.1f})  {'confere' if ep['confere'] else 'NÃO CONFERE'}")
    return pacote


def carregar_onda(caminho, inicio=0.0, duracao=None):
    """A onda em mono, 16 kHz, valores entre -1 e 1 (o librosa decodifica e reamostra)."""
    import librosa
    onda, _ = librosa.load(str(caminho), sr=TAXA, mono=True, offset=inicio, duration=duracao)
    return onda
