"""Transcrição com faster-whisper e a taxa de erro (WER) contra um gabarito.

Responsável: Belarmino Neto.

O Whisper (Radford et al., 2022) é um transformer codificador-decodificador
treinado em 680 mil horas de áudio. A entrada é o espectrograma log-mel de 80
faixas, em janelas de 30 s de áudio a 16 kHz. O faster-whisper roda o mesmo
modelo pelo CTranslate2: até 4 vezes mais rápido na CPU, sem PyTorch e sem
ffmpeg instalado (o PyAV já traz).

Medido neste notebook (i5-1335U, sem placa de vídeo), 60 s de podcast:
tiny 11,2x, base 6,4x e small 2,3x o tempo real, com o mesmo texto no trecho.
O corpus inteiro usa o base: 14 h de áudio em pouco mais de 2 h.

Cada episódio vira um JSON em dados/transcricoes/ (fora do git). Se o notebook
desligar no meio, a próxima rodada pula o que já está pronto.
"""
import json
import re
import time
import warnings

from .coleta_audio import TAXA, carregar_onda

MODELO_PADRAO = "base"
_modelos = {}


def modelo(nome=MODELO_PADRAO):
    """Carrega uma vez só (o base leva uns segundos e 150 MB de memória)."""
    if nome not in _modelos:
        warnings.filterwarnings("ignore")      # aviso de symlink do Hugging Face no Windows
        from faster_whisper import WhisperModel
        _modelos[nome] = WhisperModel(nome, device="cpu", compute_type="int8")
    return _modelos[nome]


def transcrever(onda, nome=MODELO_PADRAO, idioma="en"):
    """Segmentos com início, fim, texto e o tempo de cada palavra.

    vad_filter: o detector de voz (Silero) pula música e silêncio antes do
    Whisper, que em silêncio longo costuma inventar frase.
    """
    segmentos, _ = modelo(nome).transcribe(onda, language=idioma, vad_filter=True,
                                            word_timestamps=True, beam_size=1)
    return [{"inicio": round(s.start, 2), "fim": round(s.end, 2), "texto": s.text.strip(),
             "palavras": [[round(p.start, 2), round(p.end, 2), p.word.strip()] for p in (s.words or [])]}
            for s in segmentos]


def transcrever_episodio(caminho_mp3, pasta, nome=MODELO_PADRAO, log=print):
    """Transcreve um episódio inteiro e grava; se já existe, só devolve."""
    destino = pasta / f"{caminho_mp3.stem}.json"
    if destino.exists():
        return json.loads(destino.read_text(encoding="utf-8"))
    inicio = time.time()
    onda = carregar_onda(caminho_mp3)
    segmentos = transcrever(onda, nome)
    gasto = time.time() - inicio
    pacote = {"id": caminho_mp3.stem, "modelo": nome, "duracao": round(len(onda) / TAXA, 1),
              "segundos_de_processamento": round(gasto, 1), "segmentos": segmentos}
    pasta.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(".tmp")
    tmp.write_text(json.dumps(pacote, ensure_ascii=False), encoding="utf-8")
    tmp.replace(destino)
    log(f"  {caminho_mp3.stem}: {pacote['duracao'] / 60:.1f} min em {gasto / 60:.1f} min "
        f"({pacote['duracao'] / gasto:.1f}x o tempo real), {len(segmentos)} segmentos")
    return pacote


def palavras_normalizadas(texto):
    """Minúsculas e sem pontuação: "Token," e "token" são a mesma palavra."""
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?", texto.lower())


def wer(referencia, hipotese):
    """WER = (S + D + I) / N pela distância de Levenshtein entre as listas de palavras.

    S trocas, D palavras do gabarito que sumiram, I palavras inventadas, N o
    tamanho do gabarito. Devolve (wer, S, D, I, N).
    """
    ref, hip = palavras_normalizadas(referencia), palavras_normalizadas(hipotese)
    # custo[i][j] = (erros, S, D, I) para alinhar ref[:i] com hip[:j]
    anterior = [(j, 0, 0, j) for j in range(len(hip) + 1)]
    for i in range(1, len(ref) + 1):
        atual = [(i, 0, i, 0)]
        for j in range(1, len(hip) + 1):
            if ref[i - 1] == hip[j - 1]:
                atual.append(anterior[j - 1])
                continue
            e, s, d, ins = anterior[j - 1]
            troca = (e + 1, s + 1, d, ins)
            e, s, d, ins = anterior[j]
            remove = (e + 1, s, d + 1, ins)
            e, s, d, ins = atual[j - 1]
            insere = (e + 1, s, d, ins + 1)
            atual.append(min(troca, remove, insere))
        anterior = atual
    erros, s, d, ins = anterior[-1]
    return erros / max(len(ref), 1), s, d, ins, len(ref)


def texto_corrido(pacote):
    return " ".join(s["texto"] for s in pacote["segmentos"])
