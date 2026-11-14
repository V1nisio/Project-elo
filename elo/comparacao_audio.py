"""Etapa 2: o que se fala contra o que se escreve e o que nos derrubou; e se a fala muda na falha.

Responsável: Belarmino Neto.

H1, as três ordens. Para cada corpus, a participação de cada categoria, como na
etapa 1 (p_c = 100 * n_c / soma_j n_j), e o rho de Spearman entre cada par:
fala x escrita (os dois públicos), fala x campo, escrita x campo.

H2, a fala muda? Cada segmento da transcrição tem ritmo (palavras por minuto),
pausa antes e energia. Os segmentos que citam alguma categoria de problema são
comparados com os que não citam pelo teste de Mann-Whitney: ele ordena todos os
valores juntos e pergunta se um grupo cai sistematicamente mais alto que o
outro. Não supõe curva normal, e ritmo de fala não é normal.
  U = R_1 - n_1 (n_1 + 1) / 2, R_1 = soma das posições do grupo 1
O tamanho do efeito é r = 1 - 2U / (n_1 n_2) (correlação bisserial dos postos):
0 é nenhum efeito, e +-1 é separação total.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .categorias import ORDEM, ROTULOS
from .comparacao import br, spearman

COR = {"fala": "#e8836a", "escrita": "#3d4a8f", "campo": "#0d6a78"}
NOMES = {"fala": "Fala (podcasts)", "escrita": "Escrita (GitHub)", "campo": "Campo (diário)"}
MEDIDAS = {"palavras_por_minuto": "palavras por minuto", "pausa_antes": "pausa antes (s)", "energia_db": "energia (dB)"}


def tres_vias(fala, escrita, campo):
    """Tabela categoria a categoria e o rho de cada par de corpus."""
    corpora = {"fala": fala, "escrita": escrita, "campo": campo}
    tabela = pd.DataFrame({f"n_{k}": v["categorias"] for k, v in corpora.items()}).reindex(ORDEM)
    for k in corpora:
        tabela[f"p_{k}"] = 100 * tabela[f"n_{k}"] / tabela[f"n_{k}"].sum()
        tabela[f"posicao_{k}"] = tabela[f"p_{k}"].rank(ascending=False, method="min").astype(int)
    rhos = {"fala x escrita": spearman(tabela.p_fala, tabela.p_escrita),
            "fala x campo": spearman(tabela.p_fala, tabela.p_campo),
            "escrita x campo": spearman(tabela.p_escrita, tabela.p_campo)}
    tabela.insert(0, "categoria", [ROTULOS[c] for c in tabela.index])
    return tabela.sort_values("p_fala", ascending=False), rhos


def mann_whitney(com, sem):
    from scipy.stats import mannwhitneyu
    teste = mannwhitneyu(com, sem, alternative="two-sided")
    efeito = 1 - 2 * teste.statistic / (len(com) * len(sem))
    return teste.statistic, teste.pvalue, efeito


def fala_muda(segmentos):
    """segmentos: lista de dicts com 'categorias' e as três medidas. Uma linha por medida."""
    df = pd.DataFrame(segmentos)
    df["falha"] = df.categorias.map(bool)
    linhas = []
    for medida, rotulo in MEDIDAS.items():
        valores = df.dropna(subset=[medida])
        if medida == "palavras_por_minuto":    # segmento curtíssimo dá ritmo absurdo
            valores = valores[valores[medida].between(60, 320)]
        if medida == "pausa_antes":
            valores = valores[valores[medida] >= 0]
        com, sem = valores[valores.falha][medida], valores[~valores.falha][medida]
        u, p, r = mann_whitney(com, sem)
        linhas.append({"medida": rotulo, "mediana_com_falha": com.median(), "mediana_sem_falha": sem.median(),
                       "n_com": len(com), "n_sem": len(sem), "U": u, "p": p, "efeito_r": r})
    return pd.DataFrame(linhas)


def texto_p(p):
    """p com vírgula; abaixo de 0,001 não vale a pena mostrar os dígitos."""
    return "p < 0,001" if p < 0.001 else f"p = {br(p, 3)}"


def grafico_tres(tabela, rhos, caminho):
    fig, ax = plt.subplots(figsize=(13, 7))
    y = np.arange(len(tabela))
    for desloc, lado in ((-0.27, "fala"), (0, "escrita"), (0.27, "campo")):
        barras = ax.barh(y + desloc, tabela[f"p_{lado}"], height=0.27, color=COR[lado], label=NOMES[lado])
        ax.bar_label(barras, labels=[f"{br(v)}%" for v in tabela[f"p_{lado}"]], padding=3, fontsize=11)
    ax.set_yticks(y, tabela.categoria)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.3 * tabela[["p_fala", "p_escrita", "p_campo"]].max().max())
    ax.set_xlabel("participação entre as categorias citadas (%)")
    ax.set_title(f"O que se fala × o que se escreve × o que nos derrubou "
                 f"(ρ fala×escrita = {br(rhos['fala x escrita'], 2)}; fala×campo = {br(rhos['fala x campo'], 2)})",
                 loc="left", fontsize=15)
    ax.legend(loc="lower right", frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(caminho, dpi=200)
    plt.close(fig)


def grafico_ritmo(segmentos, resultado, caminho):
    """Distribuição de cada medida nos segmentos com falha e sem falha."""
    df = pd.DataFrame(segmentos)
    df["falha"] = df.categorias.map(bool)
    fig, eixos = plt.subplots(1, 3, figsize=(13, 5.4))
    limites = {"palavras_por_minuto": (60, 320), "pausa_antes": (0, 3), "energia_db": (-40, 0)}
    for eixo, (medida, rotulo), linha in zip(eixos, MEDIDAS.items(), resultado.itertuples()):
        a, b = limites[medida]
        grupos = [df[df.falha & df[medida].between(a, b)][medida], df[~df.falha & df[medida].between(a, b)][medida]]
        caixa = eixo.boxplot(grupos, tick_labels=["fala de falha", "o resto"], showfliers=False, patch_artist=True,
                             widths=0.55, medianprops={"color": "#18242b", "linewidth": 2})
        for parte, cor in zip(caixa["boxes"], (COR["fala"], "#ccd6d9")):
            parte.set_facecolor(cor)
        eixo.set_title(rotulo, fontsize=14)
        eixo.set_xlabel(f"{texto_p(linha.p)}; r = {br(linha.efeito_r, 2)}", fontsize=12)
        eixo.spines[["top", "right"]].set_visible(False)
    fig.suptitle("A fala muda quando o assunto é falha? (segmentos da transcrição)", x=0.01, ha="left", fontsize=17)
    fig.tight_layout()
    fig.savefig(caminho, dpi=200)
    plt.close(fig)


def espectrograma(onda, caminho, titulo, taxa=16_000):
    """O que o Whisper enxerga: 80 faixas mel, quadros de 25 ms a cada 10 ms, em dB."""
    import librosa
    mel = librosa.feature.melspectrogram(y=onda, sr=taxa, n_fft=400, hop_length=160, n_mels=80)
    db = librosa.power_to_db(mel, ref=np.max)
    fig, ax = plt.subplots(figsize=(13, 4.6))
    imagem = ax.imshow(db, origin="lower", aspect="auto", cmap="magma",
                       extent=[0, len(onda) / taxa, 0, 80], vmin=-80, vmax=0)
    ax.set_xlabel("tempo (s)")
    ax.set_ylabel("faixa mel (0 a 79)")
    ax.set_title(titulo, loc="left")
    fig.colorbar(imagem, ax=ax, fraction=0.03, label="dB")
    fig.tight_layout()
    fig.savefig(caminho, dpi=200)
    plt.close(fig)


def relatorio(tabela, rhos, ritmo, extras):
    from .comparacao import tabela_md
    linhas = ["# Elo, etapa 2: relatório da fala", "",
              *[f"- {k}: {v}" for k, v in extras.items()], "",
              "## H1: as três ordens", "", tabela_md(tabela.round(1)), "",
              *[f"- ρ {par} = {br(valor, 2)}" for par, valor in rhos.items()], "",
              "## H2: a fala muda quando o assunto é falha?", "",
              tabela_md(ritmo.round(4))]
    return "\n".join(linhas)
