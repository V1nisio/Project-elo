"""Corpus de campo: o diário (handoffs) e os logs do motor da integração real.

Responsável: Flasio Vinicius.

Regra fixa do projeto: o texto de campo nunca sai daqui. Ele é lido no lugar,
no repositório da integração, passa pelo anonimizador antes de qualquer outra
coisa e só vive em memória. O que vai para disco são números agregados.
"""
import os
import re
from collections import Counter
from pathlib import Path

from . import RAIZ
from .padroes import anonimizar

ORIGEM_PADRAO = Path(os.environ.get("ELO_CAMPO", RAIZ.parent / "trabalho_leger"))

DIARIO = [
    "moderna-salesforce-docs/Handoffs/*/*.md",
    "moderna-salesforce-docs/Handoffs/*/*.txt",
    "moderna-salesforce-docs/HANDOFF*.md",
    "integracao-moderna-salesforce-explicada/*.md",
]
LOGS = ["moderna-salesforce-sync/saida/*.log"]
# Nem abre: credencial, acesso, planilha.
PROIBIDO = re.compile(r"credenc|acesso|senha|secret|\.env|\.csv|\.xlsx", re.IGNORECASE)

MESES = "janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro".split()
DATA_ISO = re.compile(r"(20\d{2})-(\d{2})-(\d{2})")
DATA_BR = re.compile(r"\b(\d{2})/(\d{2})/(20\d{2})\b")
DATA_EXTENSO = re.compile(r"\b(\d{1,2}) de (" + "|".join(MESES) + r") de (20\d{2})")
LINHA_DE_ERRO = re.compile(r"\b(?:ERRO|ERROR|WARNING|FALHOU|falh\w*|HTTP \d{3})\b"
                           r"|\b[A-Z]+(?:_[A-Z]+)+:|\w+(?:Error|Exception)\b|exceeded")


def data_do_arquivo(caminho, texto):
    """Data da pasta (2026-09-10 - ...), senão a primeira data do cabeçalho."""
    if m := DATA_ISO.search(caminho.parent.name):
        return "-".join(m.groups())
    cabecalho = texto[:400]
    if m := DATA_ISO.search(cabecalho):
        return "-".join(m.groups())
    if m := DATA_BR.search(cabecalho):
        return f"{m[3]}-{m[2]}-{m[1]}"
    if m := DATA_EXTENSO.search(cabecalho):
        return f"{m[3]}-{MESES.index(m[2]) + 1:02d}-{int(m[1]):02d}"
    return None


def blocos_markdown(texto):
    """Parágrafos, itens de lista e linhas de tabela; sem código cercado e sem títulos.

    O bloco é a unidade de análise do diário: num handoff, cada item de lista
    costuma ser um fato (um defeito, uma decisão, um número medido).
    """
    texto = re.sub(r"```.*?```", " ", texto, flags=re.DOTALL).replace("`", "")
    blocos, atual = [], []
    for linha in texto.splitlines():
        s = linha.strip()
        if not s or s.startswith("#") or re.fullmatch(r"\|?[\s:|-]+\|?", s):
            if atual:
                blocos.append(" ".join(atual))
            atual = []
            continue
        if (re.match(r"(?:[-*]|\d+\.)\s", s) or s.startswith("|")) and atual:
            blocos.append(" ".join(atual))
            atual = []
        atual.append(re.sub(r"^(?:[-*]|\d+\.)\s+", "", s).replace("|", " ").strip())
    if atual:
        blocos.append(" ".join(atual))
    return [b for b in blocos if len(b) >= 40]


def arquivos(origem, padroes):
    encontrados = []
    for padrao in padroes:
        for arq in sorted(origem.glob(padrao)):
            if arq.is_file() and not PROIBIDO.search(arq.name) and arq not in encontrados:
                encontrados.append(arq)
    return encontrados


def ler_diario(origem=ORIGEM_PADRAO):
    """Blocos anonimizados do diário, só em memória. Devolve (documentos, máscaras, estatística)."""
    documentos, mascaras = [], Counter()
    est = {"arquivos": 0, "palavras": 0, "handoffs_datados": set()}
    for arq in arquivos(Path(origem), DIARIO):
        bruto = arq.read_text(encoding="utf-8", errors="replace")
        # Só handoff tem data de escrita; os documentos explicados são síntese e citam datas antigas.
        data = None if "explicada" in arq.parent.name else data_do_arquivo(arq, bruto)
        limpo, contagem = anonimizar(bruto)                 # antes de qualquer outra coisa
        mascaras.update(contagem)
        est["arquivos"] += 1
        est["palavras"] += len(bruto.split())
        if data:
            est["handoffs_datados"].add(arq.parent.name if DATA_ISO.match(arq.parent.name) else arq.name)
        for i, bloco in enumerate(blocos_markdown(limpo)):
            documentos.append({"id": f"{arq.parent.name[:10]}/{arq.stem}#{i}", "fonte": "diario",
                               "data": data, "prosa": bloco, "codigo": ""})
    datas = sorted(d["data"] for d in documentos if d["data"])
    est.update(handoffs_datados=len(est["handoffs_datados"]), blocos=len(documentos),
               primeira_data=datas[0] if datas else None, ultima_data=datas[-1] if datas else None)
    return documentos, mascaras, est


def ler_logs(origem=ORIGEM_PADRAO):
    """Linhas de erro dos logs do motor, anonimizadas. Devolve (documentos, máscaras, estatística)."""
    documentos, mascaras, linhas = [], Counter(), 0
    lista = arquivos(Path(origem), LOGS)
    for arq in lista:
        for i, linha in enumerate(arq.read_text(encoding="utf-8", errors="replace").splitlines()):
            linhas += 1
            linha = linha.replace("\x00", "")
            if LINHA_DE_ERRO.search(linha):
                limpa, contagem = anonimizar(linha)
                mascaras.update(contagem)
                documentos.append({"id": f"{arq.stem}:{i + 1}", "fonte": "log", "data": None,
                                   "prosa": "", "codigo": limpa})
    distintas = len({re.sub(r"\d+", "9", d["codigo"]) for d in documentos})
    return documentos, mascaras, {"arquivos": len(lista), "linhas": linhas,
                                  "linhas_de_erro": len(documentos), "mensagens_distintas": distintas}
