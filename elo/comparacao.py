"""Consolidação: o que a comunidade mais discute contra o que de fato nos derrubou.

Responsável: Belarmino Neto.

Para cada categoria c de um corpus, n_c = quantos documentos citam c (um
documento conta uma vez por categoria, por mais que repita o termo).
  participação   p_c = 100 * n_c / soma_j(n_j)          soma 100% em cada corpus
  diferença      delta_c = p_c(campo) - p_c(comunidade)  em pontos percentuais
  concordância   rho de Spearman entre as duas ordens de categorias:
                 rho = 1 - 6 * soma(d_i^2) / (n * (n^2 - 1)), d_i = diferença de posição
A participação, e não a contagem bruta, porque uma thread do GitHub é bem mais
longa que um item de handoff: o que se compara é a ênfase, não o volume.
"""
from collections import Counter

import matplotlib
matplotlib.use("Agg")                    # gera PNG sem abrir janela
import matplotlib.pyplot as plt
import pandas as pd

from .categorias import ORDEM, ROTULOS

TIPOS_SEGUROS = ["http", "erro_plataforma", "erro_oauth", "campo_custom", "excecao", "paginacao", "identificador"]
COR = {"comunidade": "#3d4a8f", "campo": "#0d6a78", "logs": "#a8371f"}
FUNDO = "#f8fafa"                         # o papel da proposta: os PNG entram direto nos slides
plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 15, "axes.titlesize": 18,
                     "figure.facecolor": FUNDO, "axes.facecolor": FUNDO, "savefig.facecolor": FUNDO})


def br(numero, casas=1):
    """Vírgula decimal, como a turma lê."""
    return f"{numero:.{casas}f}".replace(".", ",")


def agregar(resumos, sem_nomes=False, topo=30):
    """Junta os resumos de um corpus num dicionário de números (e de termos, se não for campo)."""
    resumos = list(resumos)
    achados = [a for r in resumos for a in r["achados"]]
    n_categoria = Counter(c for r in resumos for c in r["categorias"])
    agregado = {
        "n_documentos": len(resumos),
        "n_tokens": sum(r["n_tokens"] for r in resumos),
        "cobertura": sum(1 for r in resumos if r["categorias"]) / max(len(resumos), 1),
        "categorias": {c: n_categoria.get(c, 0) for c in ORDEM},
        "mecanismos": dict(Counter(m for r in resumos for ms in r["mecanismos"].values() for m in ms)),
        "so_pela_forma": sum(ms == ["forma"] for r in resumos for ms in r["mecanismos"].values()),
        "so_pela_regex": sum(ms == ["regex"] for r in resumos for ms in r["mecanismos"].values()),
        # frequência de documento: uma thread com o mesmo log colado 40 vezes conta uma vez
        "lemas": Counter(lema for r in resumos for lema in set(r["lemas"])).most_common(topo),
        "sintagmas": Counter(s for r in resumos for s in set(r["sintagmas"])).most_common(topo),
        "entidades": Counter(rotulo for r in resumos for rotulo, _ in r["entidades"]).most_common(),
        "achados_por_tipo": dict(Counter(a.tipo for a in achados).most_common()),
        "achados_valores": {t: Counter(a.valor for a in achados if a.tipo == t).most_common(15) for t in TIPOS_SEGUROS},
        "cpf_classes": dict(Counter(a.detalhe for a in achados if a.tipo == "cpf")),
        "por_documento": [{"id": r["id"], "fonte": r["fonte"], "data": r["data"], "categorias": r["categorias"]}
                          for r in resumos],
    }
    if not sem_nomes:
        agregado["nomes_de_entidade"] = Counter(texto for r in resumos for rotulo, texto in r["entidades"]
                                                if rotulo in {"ORG", "PRODUCT"}).most_common(topo)
        agregado["exemplos"] = {c: [{"titulo": r["titulo"], "url": r["url"], "comentarios": r["n_comentarios"]}
                                    for r in sorted((r for r in resumos if c in r["categorias"]),
                                                    key=lambda r: -r["n_comentarios"])[:3]] for c in ORDEM}
    return agregado


def spearman(a, b):
    """Pearson entre as posições é o Spearman (empate fica com a posição média)."""
    return a.rank().corr(b.rank())


def comparar(comunidade, campo):
    """Tabela categoria a categoria e o rho entre as duas ordens."""
    tabela = pd.DataFrame({"n_comunidade": comunidade["categorias"], "n_campo": campo["categorias"]}).reindex(ORDEM)
    for lado in ("comunidade", "campo"):
        tabela[f"p_{lado}"] = 100 * tabela[f"n_{lado}"] / tabela[f"n_{lado}"].sum()
        tabela[f"posicao_{lado}"] = tabela[f"p_{lado}"].rank(ascending=False, method="min").astype(int)
    tabela["delta_pp"] = tabela.p_campo - tabela.p_comunidade
    rho = spearman(tabela.p_comunidade, tabela.p_campo)
    tabela.insert(0, "categoria", [ROTULOS[c] for c in tabela.index])
    return tabela.sort_values("p_campo", ascending=False), rho


def grafico_categorias(tabela, rho, caminho):
    fig, ax = plt.subplots(figsize=(13, 6.6))
    y = range(len(tabela))
    for desloc, lado, rotulo in ((-0.2, "comunidade", "Comunidade (GitHub)"), (0.2, "campo", "Campo (diário)")):
        barras = ax.barh([i + desloc for i in y], tabela[f"p_{lado}"], height=0.4, color=COR[lado], label=rotulo)
        ax.bar_label(barras, labels=[f"{br(v)}%" for v in tabela[f"p_{lado}"]], padding=4, fontsize=14)
    ax.set_yticks(list(y), tabela.categoria)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.35 * tabela[["p_comunidade", "p_campo"]].max().max())   # folga para rótulo e legenda
    ax.set_xlabel("participação entre as categorias citadas (%)")
    ax.set_title(f"O que se discute × o que nos derrubou (ρ de Spearman = {br(rho, 2)})", loc="left")
    ax.legend(loc="lower right", frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(caminho, dpi=200)
    plt.close(fig)


def grafico_evolucao(campo, caminho):
    """Participação semanal de cada categoria no diário (só blocos com data)."""
    linhas = [{"data": d["data"], **{c: c in d["categorias"] for c in ORDEM}}
              for d in campo["por_documento"] if d["data"] and d["fonte"] == "diario"]
    df = pd.DataFrame(linhas)
    df["semana"] = pd.to_datetime(df["data"]).dt.to_period("W").dt.start_time
    n = df.groupby("semana")[ORDEM].sum()
    p = 100 * n.div(n.sum(axis=1), axis=0)
    fig, ax = plt.subplots(figsize=(13, 6.2))
    imagem = ax.imshow(p.T.values, aspect="auto", cmap="YlGnBu")
    ax.set_yticks(range(len(ORDEM)), [ROTULOS[c] for c in ORDEM])
    ax.set_xticks(range(len(p)), [s.strftime("%d/%m") for s in p.index])
    ax.set_xlabel("semana do handoff")
    ax.set_title("O diário semana a semana (% das categorias citadas)", loc="left")
    fig.colorbar(imagem, ax=ax, fraction=0.03)
    fig.tight_layout()
    fig.savefig(caminho, dpi=200)
    plt.close(fig)
    return p


def grafico_termos(pares, titulo, cor, caminho, quantos=15):
    pares = pares[:quantos][::-1]
    fig, ax = plt.subplots(figsize=(9.5, 5.6))
    barras = ax.barh([t for t, _ in pares], [n for _, n in pares], color=cor)
    ax.bar_label(barras, labels=[f"{n:,}".replace(",", ".") for _, n in pares], padding=4, fontsize=14)
    ax.set_title(titulo, loc="left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(caminho, dpi=200)
    plt.close(fig)


def tabela_md(df):
    linhas = ["| " + " | ".join(map(str, df.columns)) + " |", "|" + "---|" * len(df.columns)]
    linhas += ["| " + " | ".join(map(str, valores)) + " |" for valores in df.itertuples(index=False)]
    return "\n".join(linhas)


def relatorio(tabela, rho, comunidade, campo, logs, extras):
    """Markdown com tudo o que vai para os slides, só números e termos."""
    def lista(pares, n=12):
        return ", ".join(f"{t} ({q})" for t, q in pares[:n])

    maior = tabela.sort_values("delta_pp")
    linhas = [
        "# Elo, etapa 1: relatório", "",
        f"- Comunidade: {comunidade['n_documentos']} issues, {comunidade['n_tokens']:,} tokens, "
        f"{100 * comunidade['cobertura']:.0f}% com alguma categoria".replace(",", "."),
        f"- Campo: {campo['n_documentos']} blocos do diário, {campo['n_tokens']:,} tokens, "
        f"{100 * campo['cobertura']:.0f}% com alguma categoria".replace(",", "."),
        f"- Logs do motor: {logs['n_documentos']} linhas de erro", "",
        "## Categorias", "",
        tabela_md(tabela.round(1)), "",
        f"ρ de Spearman = {br(rho, 2)}. Mais acima no campo do que na comunidade: "
        f"{maior.iloc[-1]['categoria']} (+{br(maior.iloc[-1]['delta_pp'])} p.p.). "
        f"Mais abaixo: {maior.iloc[0]['categoria']} ({br(maior.iloc[0]['delta_pp'])} p.p.).", "",
        "## Termos", "",
        f"- Lemas da comunidade: {lista(comunidade['lemas'])}",
        f"- Sintagmas da comunidade: {lista(comunidade['sintagmas'])}",
        f"- Lemas do campo (sem nomes próprios): {lista(campo['lemas'])}",
        f"- Sintagmas do campo: {lista(campo['sintagmas'])}", "",
        "## O que a máquina gritou (logs)", "",
        f"- Erros de plataforma: {lista(logs['achados_valores']['erro_plataforma'], 10)}",
        f"- Campos customizados: {lista(logs['achados_valores']['campo_custom'], 5)}",
        f"- HTTP: {lista(logs['achados_valores']['http'], 5)}",
        f"- Exceções: {lista(logs['achados_valores']['excecao'], 5)}", "",
        "## Coleta e proteção", "",
        *[f"- {chave}: {valor}" for chave, valor in extras.items()],
    ]
    return "\n".join(linhas)
