"""Sintético falado: problemas de integração conhecidos, ditos pela voz do Windows.

Responsável: Theo Haiek.

Como o sintético da etapa 1, nada aqui é dado real, e tudo tem gabarito: o
texto exato, a categoria de cada frase e o lugar de cada pausa inserida. Uma
frase por categoria, em inglês (a língua dos podcasts), com os códigos HTTP
falados por extenso, do jeito que se fala num podcast ("four twenty nine").

Os quatro defeitos são os de formato que quebram um pipeline de áudio, como os
de texto quebravam a integração:
  ruido         chiado branco a 10 dB abaixo da fala (SNR = 10 dB)
  estereo_44k   dois canais a 44,1 kHz, o formato de CD, no lugar de mono 16 kHz
  volume_baixo  a mesma fala 30 dB mais baixa
  clipping      ganho de 10 vezes: a onda bate no teto e achata

Os arquivos ficam em dados/sintetico_falado/ e sobem para o git, porque a voz
muda de um Windows para outro.
"""
import json
import os
import tempfile

import numpy as np

TAXA = 16_000
VOZ = "Zira"                 # Microsoft Zira, inglês dos Estados Unidos
PAUSAS = [0.6, 1.0, 0.8, 1.4, 0.7, 1.2, 0.9, 1.5, 0.6]     # s, entre as 10 frases

FRASES = [
    ("autenticacao", "After the deploy, every request came back with error four oh one, because the access token had expired."),
    ("limite_taxa", "The nightly sync hit the rate limit, and the API answered with error four twenty nine: too many requests."),
    ("paginacao", "We read the accounts with offset pagination, and two pages came back in a different order."),
    ("duplicidade", "The upsert had no external ID, so the same customer was created twice, as a duplicate account."),
    ("mapeamento", "The custom field was renamed in the CRM, and the field mapping kept sending the old name."),
    ("formato", "One system sent the date format as day, month, year, and the other read it as month, day, year."),
    ("ordem", "The opportunity arrived before its parent account: a race condition between two parallel jobs."),
    ("silenciosa", "The job reported success, but the records never arrived. It failed silently, with no error at all."),
    ("rede", "The connection timed out, and the server answered with error five oh three: service unavailable."),
    ("ambiente", "It worked in the sandbox, but production had a different configuration for the same variable."),
]


def falar(frase):
    """Uma frase em onda mono de 16 kHz, sem o silêncio que a voz põe nas pontas."""
    import librosa
    import pyttsx3
    import soundfile as sf
    motor = pyttsx3.init()
    vozes = [v.id for v in motor.getProperty("voices") if VOZ in v.name]
    if not vozes:
        raise RuntimeError(f"a voz {VOZ} não está instalada neste Windows; use os arquivos já gerados")
    motor.setProperty("voice", vozes[0])
    motor.setProperty("rate", 165)
    caminho = os.path.join(tempfile.gettempdir(), "elo_frase.wav")
    motor.save_to_file(frase, caminho)
    motor.runAndWait()
    onda, taxa = sf.read(caminho, dtype="float32")
    onda = librosa.resample(onda, orig_sr=taxa, target_sr=TAXA)
    onda, _ = librosa.effects.trim(onda, top_db=35, frame_length=400, hop_length=160)
    return onda


def montar():
    """As 10 frases com as pausas do gabarito entre elas."""
    pedacos, gabarito, t = [], [], 0.0
    for i, (categoria, frase) in enumerate(FRASES):
        onda = falar(frase)
        gabarito.append({"id": f"fala-{i + 1:02d}", "categoria": categoria, "texto": frase,
                         "inicio": round(t, 3), "fim": round(t + len(onda) / TAXA, 3)})
        pedacos.append(onda)
        t += len(onda) / TAXA
        if i < len(PAUSAS):
            pedacos.append(np.zeros(int(PAUSAS[i] * TAXA), dtype=np.float32))
            t += PAUSAS[i]
    onda = np.concatenate(pedacos)
    return 0.7 * onda / np.abs(onda).max(), gabarito


def defeitos(onda, semente=42):
    """As quatro versões estragadas da mesma fala."""
    import librosa
    rng = np.random.default_rng(semente)
    potencia = np.mean(onda[np.abs(onda) > 0.01] ** 2)
    ruido = onda + rng.normal(0, np.sqrt(potencia / 10 ** (10 / 10)), len(onda)).astype(np.float32)
    cd = librosa.resample(onda, orig_sr=TAXA, target_sr=44_100)
    return {
        "ruido": (np.clip(ruido, -1, 1), TAXA),
        "estereo_44k": (np.stack([cd, 0.8 * cd], axis=1), 44_100),
        "volume_baixo": (onda * 10 ** (-30 / 20), TAXA),
        "clipping": (np.clip(onda * 10, -1, 1), TAXA),
    }


def gerar(pasta):
    """Grava limpo + 4 defeitos em FLAC (sem perda, metade do WAV) e o gabarito."""
    import soundfile as sf
    pasta.mkdir(parents=True, exist_ok=True)
    onda, gabarito = montar()
    versoes = {"limpo": (onda, TAXA), **defeitos(onda)}
    for nome, (dados, taxa) in versoes.items():
        sf.write(pasta / f"{nome}.flac", dados, taxa, subtype="PCM_16")
    pausas = [(gabarito[i]["fim"], gabarito[i + 1]["inicio"]) for i in range(len(gabarito) - 1)]
    pacote = {"taxa": TAXA, "voz": VOZ, "versoes": list(versoes), "frases": gabarito, "pausas": pausas}
    (pasta / "gabarito.json").write_text(json.dumps(pacote, ensure_ascii=False, indent=1), encoding="utf-8")
    return pacote


def carregar(pasta):
    return json.loads((pasta / "gabarito.json").read_text(encoding="utf-8"))
