"""O som medido: energia, silêncio, pausas e ritmo de fala.

Responsável: Theo Haiek.

A onda chega em mono, 16 kHz (coleta_audio.carregar_onda). Ela é cortada em
quadros de 25 ms (N = 400 amostras) que andam de 10 em 10 ms (160 amostras),
os mesmos números do Whisper. Para cada quadro:
  energia    RMS = raiz( (1/N) * soma(x[n]^2) )
  nível      L = 20 * log10(RMS / RMS_max)  em dB; 0 dB é o quadro mais forte
  silêncio   L abaixo de -35 dB (o top_db do librosa)
  pausa      silêncio de 300 ms ou mais entre dois trechos de fala
O ritmo vem da transcrição: palavras por minuto, contando do começo da primeira
palavra ao fim da última de cada segmento, para a pausa não entrar na conta.
"""
import numpy as np

QUADRO = 400          # 25 ms a 16 kHz
SALTO = 160           # 10 ms
TOP_DB = 35           # abaixo de -35 dB do quadro mais forte é silêncio
PAUSA_MIN = 0.3       # s
TAXA = 16_000


def quadros(onda):
    """Matriz (n_quadros, N) sem copiar a onda: cada linha é uma janela de 25 ms."""
    if len(onda) < QUADRO:
        onda = np.pad(onda, (0, QUADRO - len(onda)))
    n = 1 + (len(onda) - QUADRO) // SALTO
    return np.lib.stride_tricks.as_strided(onda, (n, QUADRO), (onda.strides[0] * SALTO, onda.strides[0]))


def rms(onda):
    """A fórmula do slide, em numpy puro (o teste confere contra o librosa)."""
    q = quadros(onda.astype(np.float64))
    return np.sqrt(np.mean(q ** 2, axis=1))


def em_db(energia):
    """L = 20 log10(RMS / RMS_max). O piso de 1e-10 evita log de zero."""
    return 20 * np.log10(np.maximum(energia, 1e-10) / max(energia.max(), 1e-10))


def cruzamentos_por_zero(onda):
    """Fração de amostras em que a onda troca de sinal: chiado tem muito, vogal tem pouco."""
    return float(np.mean(np.signbit(onda[1:]) != np.signbit(onda[:-1]))) if len(onda) > 1 else 0.0


def trechos_de_fala(onda):
    """Intervalos (início, fim) em segundos onde o nível passa de -35 dB."""
    import librosa
    intervalos = librosa.effects.split(onda, top_db=TOP_DB, frame_length=QUADRO, hop_length=SALTO)
    return [(a / TAXA, b / TAXA) for a, b in intervalos]


def pausas(trechos, minimo=PAUSA_MIN):
    """Os buracos entre trechos de fala que duram `minimo` segundos ou mais."""
    return [(fim, inicio) for (_, fim), (inicio, _) in zip(trechos, trechos[1:]) if inicio - fim >= minimo]


def medir(onda):
    """Os números de um áudio inteiro."""
    duracao = len(onda) / TAXA
    trechos = trechos_de_fala(onda)
    buracos = pausas(trechos)
    fala = sum(b - a for a, b in trechos)
    nivel = em_db(rms(onda))
    falando = nivel > -TOP_DB
    return {
        "duracao": round(duracao, 1),
        "fala": round(fala, 1),
        "razao_de_fala": round(fala / max(duracao, 1e-9), 3),
        "pausas": len(buracos),
        "pausas_por_minuto": round(len(buracos) / max(duracao / 60, 1e-9), 1),
        "pausa_media": round(float(np.mean([b - a for a, b in buracos])), 2) if buracos else 0.0,
        "energia_db_fala": round(float(nivel[falando].mean()), 1) if falando.any() else None,
        "energia_db_desvio": round(float(nivel[falando].std()), 1) if falando.any() else None,
        "cruzamentos_por_zero": round(cruzamentos_por_zero(onda), 4),
    }


def silencio_antes(buracos, t, folga=0.4):
    """O silêncio medido no sinal que termina perto de t (o início de um segmento).

    O tempo do Whisper não serve: em metade dos segmentos o início é colado no fim
    do anterior. O sinal diz onde o nível caiu abaixo de -35 dB de verdade.
    """
    perto = [fim - inicio for inicio, fim in buracos if abs(fim - t) <= folga]
    return max(perto, default=0.0)


def medir_segmentos(onda, segmentos):
    """Ritmo, pausa antes (medida no sinal) e energia de cada segmento da transcrição."""
    nivel = em_db(rms(onda))
    buracos = pausas(trechos_de_fala(onda), minimo=0.0)
    saida, fim_anterior = [], None
    for s in segmentos:
        palavras = s["palavras"]
        falado = (palavras[-1][1] - palavras[0][0]) if palavras else s["fim"] - s["inicio"]
        a, b = int(s["inicio"] * TAXA / SALTO), max(int(s["fim"] * TAXA / SALTO), int(s["inicio"] * TAXA / SALTO) + 1)
        saida.append({
            "palavras_por_minuto": round(60 * len(palavras) / falado, 1) if palavras and falado > 0.5 else None,
            "pausa_antes": round(silencio_antes(buracos, s["inicio"]), 2) if fim_anterior is not None else None,
            "energia_db": round(float(nivel[a:b].mean()), 1) if b <= len(nivel) else None,
        })
        fim_anterior = s["fim"]
    return saida


def grafico_onda(onda, caminho, titulo, segundos=60):
    """A onda e a energia em dB do primeiro minuto, com os silêncios sombreados."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from . import comparacao          # noqa: F401  (só para herdar fonte e fundo dos gráficos)
    trecho = onda[:segundos * TAXA]
    nivel = em_db(rms(trecho))
    t_onda = np.arange(len(trecho)) / TAXA
    t_nivel = np.arange(len(nivel)) * SALTO / TAXA
    fig, (cima, baixo) = plt.subplots(2, 1, figsize=(13, 6.2), sharex=True)
    cima.plot(t_onda, trecho, color="#3d4a8f", linewidth=0.4)
    cima.set_ylabel("amplitude")
    cima.set_title(titulo, loc="left")
    baixo.plot(t_nivel, nivel, color="#0d6a78", linewidth=1)
    baixo.axhline(-TOP_DB, color="#a8371f", linestyle="--", linewidth=1.2, label=f"limiar de silêncio ({-TOP_DB} dB)")
    for inicio, fim in pausas(trechos_de_fala(trecho)):
        for eixo in (cima, baixo):
            eixo.axvspan(inicio, fim, color="#e8836a", alpha=0.25, linewidth=0)
    baixo.set_ylabel("energia (dB)")
    baixo.set_xlabel("tempo (s); em laranja, as pausas de 300 ms ou mais")
    baixo.set_ylim(-80, 3)
    baixo.legend(loc="lower right", frameon=False)
    for eixo in (cima, baixo):
        eixo.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(caminho, dpi=200)
    plt.close(fig)
