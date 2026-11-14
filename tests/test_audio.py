"""Testes da etapa 2. Só valor sintético: onda gerada aqui, nenhum áudio real."""
import numpy as np

from elo import coleta_audio, sinal, transcricao
from elo.padroes import extrair, normalizar_numeros_falados, valor_falado

TAXA = 16_000


def tom(segundos, freq=440, amplitude=0.5):
    t = np.arange(int(segundos * TAXA)) / TAXA
    return (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def test_rms_bate_com_a_formula():
    # seno de amplitude A tem RMS = A / raiz(2)
    assert np.allclose(sinal.rms(tom(1))[5:-5], 0.5 / np.sqrt(2), atol=1e-3)


def test_rms_bate_com_o_librosa():
    import librosa
    onda = tom(1) + 0.1 * tom(1, 1300)
    nosso = sinal.rms(onda)
    deles = librosa.feature.rms(y=onda, frame_length=400, hop_length=160, center=False)[0]
    assert np.allclose(nosso, deles, atol=1e-4)


def test_em_db_poe_o_mais_forte_em_zero():
    nivel = sinal.em_db(np.array([1.0, 0.1, 0.01]))
    assert np.allclose(nivel, [0, -20, -40])


def test_pausa_inserida_e_achada():
    onda = np.concatenate([tom(1), np.zeros(int(0.8 * TAXA), np.float32), tom(1)])
    achadas = sinal.pausas(sinal.trechos_de_fala(onda))
    assert len(achadas) == 1
    inicio, fim = achadas[0]
    assert abs(inicio - 1.0) < 0.05 and abs(fim - 1.8) < 0.05


def test_pausa_curta_nao_conta():
    onda = np.concatenate([tom(1), np.zeros(int(0.1 * TAXA), np.float32), tom(1)])
    assert sinal.pausas(sinal.trechos_de_fala(onda)) == []


def test_ruido_cruza_mais_o_zero_que_vogal():
    ruido = np.random.default_rng(0).normal(0, 0.3, TAXA).astype(np.float32)
    assert sinal.cruzamentos_por_zero(ruido) > 5 * sinal.cruzamentos_por_zero(tom(1, 200))


def test_wer_conta_troca_perda_e_insercao():
    taxa, s, d, i, n = transcricao.wer("the token expired after the sync", "the token expire after sync now")
    assert (s, d, i, n) == (1, 1, 1, 6) and taxa == 0.5


def test_wer_ignora_caixa_e_pontuacao():
    assert transcricao.wer("Error 429, too many requests.", "error 429 too many requests")[0] == 0


def test_numero_falado_vira_codigo_http():
    assert valor_falado("four twenty nine") == 429
    assert valor_falado("five oh three") == 503
    assert valor_falado("four hundred and four") == 404
    texto, trocas = normalizar_numeros_falados("the API answered with error four twenty-nine")
    assert texto.endswith("error 429") and trocas == 1
    assert ("http", "429") in [(a.tipo, a.valor) for a in extrair(texto)]


def test_numero_falado_que_nao_e_http_fica():
    for frase in ("four or five times", "five fifty users", "four thousand rows"):
        assert normalizar_numeros_falados(frase) == (frase, 0)


def test_duracao_do_rss_em_tres_formatos():
    assert coleta_audio.segundos("3245") == 3245
    assert coleta_audio.segundos("54:05") == 3245
    assert coleta_audio.segundos("1:02:30") == 3750


def test_selecao_por_sistema_e_nao_por_problema():
    lista = [{"titulo": t} for t in ("Scaling Airbyte to 1.0", "Continuous Integration at scale",
                                    "Ryan Singer on Shape Up", "Leveling up with the Singer SDK",
                                    "Data integration patterns", "How we fixed rate limits")]
    escolhidos = [e["titulo"] for e in coleta_audio.selecionar(lista, 10)]
    assert escolhidos == ["Scaling Airbyte to 1.0", "Leveling up with the Singer SDK", "Data integration patterns"]


def test_pausa_antes_vem_do_sinal_e_nao_do_whisper():
    # silêncio de 0,8 s entre 1,0 e 1,8 s; o Whisper diria que o segmento começa em 1,75
    buracos = [(1.0, 1.8)]
    assert abs(sinal.silencio_antes(buracos, 1.75) - 0.8) < 1e-9
    assert sinal.silencio_antes(buracos, 5.0) == 0.0
