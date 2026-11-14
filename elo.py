"""Elo: o que quebra entre dois sistemas. Etapa 1 lida em texto; etapa 2 ouvida em áudio.

Cada subcomando chama o módulo de um integrante. Etapa 1:
  coletar    Flasio Vinicius   issues do GitHub pela API REST              elo/coleta.py
  campo      Flasio Vinicius   diário e logs da integração, anonimizados   elo/campo.py
  sintetico  Theo Haiek        casos sintéticos com os defeitos reais      elo/sintetico.py
  extrair    Theo Haiek        expressões regulares sobre um corpus        elo/padroes.py
  analisar   Belarmino Neto    spaCy: lemas, sintagmas, entidades          elo/analisador.py
  comparar   Belarmino Neto    comunidade x campo, gráficos e relatório    elo/comparacao.py
  tudo       a equipe          a etapa inteira, de ponta a ponta
Etapa 2:
  podcasts         Flasio Vinicius   API da Apple, RSS e MP3 conferidos   elo/coleta_audio.py
  sintetico-audio  Theo Haiek        falas sintéticas com 4 defeitos      elo/sintetico_audio.py
  sinal            Theo Haiek        energia, silêncio, pausas, ritmo     elo/sinal.py
  transcrever      Belarmino Neto    faster-whisper e WER                 elo/transcricao.py
  comparar-audio   Belarmino Neto    fala x escrita x campo; a fala muda? elo/comparacao_audio.py
"""
import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

from elo import DADOS, SAIDA, campo, coleta, padroes, sintetico
from elo.categorias import ROTULOS
from elo.comparacao import br

PII = {"cpf", "telefone", "email", "segredo", "nome_repetido", "id_sf", "preenchimento", "chave_mod"}


def tabelas_largas():
    """pandas só carrega nos comandos que imprimem tabela (custa 1,2 s no começo)."""
    import pandas as pd
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", 60)


def salvar(nome, dados):
    SAIDA.mkdir(exist_ok=True)
    (SAIDA / nome).write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")


def carregar(nome, args):
    """Documentos de um corpus. O de campo é lido na hora e nunca é gravado."""
    if nome == "comunidade":
        return coleta.carregar(DADOS / "comunidade.json", getattr(args, "limite", None))["documentos"]
    if nome == "sintetico":
        arquivo = DADOS / "sintetico.json"
        return json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else sintetico.gerar()
    if nome == "podcasts":
        return documentos_da_fala(getattr(args, "limite", None))
    if nome == "sintetico-falado":
        return documentos_do_sintetico_falado()
    documentos, _, _ = campo.ler_diario(args.origem)
    return documentos


FALA = DADOS / "sintetico_falado"
AUDIO = DADOS / "audio"
TRANSCRICOES = DADOS / "transcricoes"


def texto_da_fala(texto):
    """Toda fala passa pelo anonimizador e depois pelos números falados ("four twenty nine" -> 429)."""
    texto, _ = padroes.anonimizar(texto)
    return padroes.normalizar_numeros_falados(texto)[0]


def episodios():
    return json.loads((DADOS / "podcasts.json").read_text(encoding="utf-8"))["episodios"]


def documentos_da_fala(limite=None):
    """Cada segmento da transcrição (uma frase, mais ou menos) é um documento."""
    documentos = []
    for ep in episodios():
        arquivo = TRANSCRICOES / f"{ep['id']}.json"
        if not arquivo.exists():
            continue
        pacote = json.loads(arquivo.read_text(encoding="utf-8"))
        documentos += [{"id": f"{ep['id']}:{i:04d}", "fonte": ep["fonte"], "data": ep["data"],
                        "prosa": texto_da_fala(s["texto"]), "codigo": ""} for i, s in enumerate(pacote["segmentos"])]
    return documentos[:limite]


def documentos_do_sintetico_falado(versao="limpo"):
    """As palavras transcritas voltam para a frase do gabarito pelo tempo em que foram ditas."""
    gabarito = json.loads((FALA / "gabarito.json").read_text(encoding="utf-8"))
    pacote = json.loads((FALA / f"transcricao_{versao}.json").read_text(encoding="utf-8"))
    palavras = [p for s in pacote["segmentos"] for p in s["palavras"]]
    documentos = []
    for f in gabarito["frases"]:
        dita = " ".join(p for a, b, p in palavras if f["inicio"] - 0.3 <= (a + b) / 2 <= f["fim"] + 0.3)
        documentos.append({"id": f["id"], "fonte": "sintetico-falado", "data": None, "esperada": f["categoria"],
                           "gabarito": f["texto"], "dita": dita, "prosa": texto_da_fala(dita), "codigo": ""})
    return documentos


def cmd_coletar(args):
    # Na demonstração ao vivo, --destino dados/demo.json preserva a coleta completa.
    pacote = coleta.coletar(Path(args.destino), args.max_por_fonte, args.comentarios,
                            token=os.environ.get("GITHUB_TOKEN"))
    abertas = sum(1 for c in pacote["conferencias"].values() if not c["fecha"])
    print(f"conferência geral: {len(pacote['conferencias']) - abertas} fontes fecham, {abertas} não fecham")


def cmd_campo(args):
    documentos, mascaras, est = campo.ler_diario(args.origem)
    logs, mascaras_logs, est_logs = campo.ler_logs(args.origem)
    print(f"origem: {args.origem}")
    print(f"diário: {est['arquivos']} arquivos, {est['palavras']:,} palavras, {est['handoffs_datados']} handoffs "
          f"datados ({est['primeira_data']} a {est['ultima_data']}), {est['blocos']:,} blocos".replace(",", "."))
    print(f"logs:   {est_logs['arquivos']} arquivos, {est_logs['linhas']:,} linhas, {est_logs['linhas_de_erro']:,} "
          f"de erro, {est_logs['mensagens_distintas']} mensagens distintas".replace(",", "."))
    print("máscaras aplicadas antes de qualquer análise:")
    for tipo, n in (mascaras + mascaras_logs).most_common():
        print(f"  {tipo:15} {n:6}")
    salvar("campo_estatisticas.json", {"diario": est, "logs": est_logs,
                                       "mascaras": dict(mascaras + mascaras_logs)})


def cmd_sintetico(args):
    documentos = sintetico.gerar(args.n, args.semente)
    DADOS.mkdir(exist_ok=True)
    (DADOS / "sintetico.json").write_text(json.dumps(documentos, ensure_ascii=False, indent=1), encoding="utf-8")
    for d in documentos:
        print(f"{d['id']}  [{d['defeito']}]\n    {d['prosa']}")
    print(f"{len(documentos)} casos em dados/sintetico.json (semente {args.semente})")


def resumo_achados(achados, mostra_valores):
    por_tipo = Counter(a.tipo for a in achados)
    for tipo, n in por_tipo.most_common():
        linha = f"  {tipo:16} {n:6}"
        if tipo == "cpf" or (tipo == "chave_mod" and not mostra_valores):
            # no campo, a chave real (MOD-PAC-<id> aponta um paciente) aparece só como contagem por tipo
            linha += "   " + ", ".join(f"{k}: {v}" for k, v in Counter(a.detalhe for a in achados if a.tipo == tipo).items())
            repetidos = [v for v, q in Counter(a.valor for a in achados if a.tipo == "cpf").items() if q > 1]
            if tipo == "cpf" and repetidos:
                linha += f"; mesmo CPF em mais de um documento: {len(repetidos)}"
        elif mostra_valores or tipo not in PII:
            linha += "   " + ", ".join(f"{v} ({q})" for v, q in Counter(a.valor for a in achados if a.tipo == tipo).most_common(4))
        print(linha)
    return dict(por_tipo)


def cmd_extrair(args):
    documentos = carregar(args.corpus, args)
    if args.corpus == "sintetico":
        for d in documentos:
            achados = padroes.extrair(d["prosa"])
            limpo, _ = padroes.anonimizar(d["prosa"])
            print(f"\n{d['id']} [{d['defeito']}] {d['prosa']}")
            for a in achados:
                print(f"    {a.tipo:15} {a.valor:32} {a.detalhe}")
            print(f"    anonimizado: {limpo}")
    elif args.corpus == "sintetico-falado":
        for d in documentos:
            print(f"\n{d['id']} [{d['esperada']}] ouvido: {d['dita']}")
            print(f"    depois das regex: {d['prosa']}")
            for a in padroes.extrair(d["prosa"]):
                print(f"    {a.tipo:15} {a.valor:32} {a.detalhe}")
    elif args.corpus == "podcasts":
        trocas = sum(padroes.normalizar_numeros_falados(padroes.anonimizar(s["texto"])[0])[1]
                     for ep in episodios() if (TRANSCRICOES / f"{ep['id']}.json").exists()
                     for s in json.loads((TRANSCRICOES / f"{ep['id']}.json").read_text(encoding="utf-8"))["segmentos"])
        print(f"códigos HTTP ditos por extenso e trocados por dígitos: {trocas}")
    elif args.corpus == "comunidade":
        for d in documentos[:args.exemplos]:
            print(f"\n{d['fonte']} #{d['numero']}: {d['titulo']}")
            for a in padroes.extrair(d["prosa"] + "\n" + d["codigo"])[:8]:
                print(f"    {a.tipo:15} {a.valor[:40]:40} {a.detalhe}")
    achados = [a for d in documentos for a in padroes.extrair(d["prosa"] + "\n" + d.get("codigo", ""))]
    print(f"\n{args.corpus}: {len(documentos)} documentos, {len(achados)} achados")
    resultado = {"diario": resumo_achados(achados, args.corpus != "campo")}
    if args.corpus == "campo":                # campo: valores pessoais nunca aparecem, só contagem
        logs, _, _ = campo.ler_logs(args.origem)
        achados_logs = [a for d in logs for a in padroes.extrair(d["codigo"])]
        print(f"\nlogs do motor: {len(logs)} linhas de erro, {len(achados_logs)} achados")
        resultado["logs"] = resumo_achados(achados_logs, False)
    salvar(f"achados_{args.corpus}.json", resultado)


def resumos_dos_logs(logs):
    """Logs não têm prosa: categoria só pelas regex, sem passar pelo spaCy."""
    for d in logs:
        achados = padroes.extrair(d["codigo"])
        categorias = sorted(padroes.sinais_de_categoria(achados))
        yield {"id": d["id"], "fonte": "log", "data": None, "categorias": categorias,
               "mecanismos": {c: ["regex"] for c in categorias}, "n_tokens": 0,
               "lemas": [], "sintagmas": [], "entidades": [], "achados": achados}


def cmd_analisar(args):
    from elo.analisador import Analisador
    from elo.comparacao import agregar
    tabelas_largas()
    inicio = time.time()
    documentos = carregar(args.corpus, args)[:args.limite]
    analisador = Analisador("pt" if args.corpus in ("campo", "sintetico") else "en")
    if args.mostrar or args.doc:
        if args.corpus == "campo":
            print("campo não mostra texto: só números saem do diário (regra fixa do projeto)")
        else:
            escolhidos = [d for d in documentos if d["id"] == args.doc] if args.doc else documentos[:args.mostrar]
            for d in escolhidos:
                print(f"\n{d['id']}: {d['prosa'][:200]}")
                print(analisador.tabela(d["prosa"][:600]).to_string(index=False))
    sem_nomes = args.corpus == "campo"
    agregado = agregar(analisador.analisar(documentos, sem_nomes=sem_nomes), sem_nomes=sem_nomes)
    if args.corpus == "campo":
        logs, _, _ = campo.ler_logs(args.origem)
        agregado["logs"] = agregar(resumos_dos_logs(logs), sem_nomes=True)
    # Uma amostra (--limite) não pode substituir a análise completa que o comparar lê.
    arquivo = f"analise_{args.corpus}{'_amostra' if args.limite else ''}.json"
    salvar(arquivo, agregado)
    print(f"\n{args.corpus}: {agregado['n_documentos']} documentos, {agregado['n_tokens']:,} tokens, "
          f"{100 * agregado['cobertura']:.0f}% com categoria, {time.time() - inicio:.1f} s".replace(",", "."))
    print("categorias (documentos que citam):")
    for c, n in sorted(agregado["categorias"].items(), key=lambda x: -x[1]):
        print(f"  {ROTULOS[c]:32} {n:6}")
    print("lemas:", ", ".join(f"{t} ({n})" for t, n in agregado["lemas"][:15]))
    print("sintagmas:", ", ".join(f"{t} ({n})" for t, n in agregado["sintagmas"][:10]))
    print("entidades:", ", ".join(f"{t} ({n})" for t, n in agregado["entidades"][:8]))
    print(f"mecanismos: {agregado['mecanismos']}; marcações que só a forma literal achou: "
          f"{agregado['so_pela_forma']}; só a regex: {agregado['so_pela_regex']}")
    if args.corpus == "sintetico-falado":
        acertos = sum(d["esperada"] in r["categorias"] for d, r in zip(documentos, agregado["por_documento"]))
        print(f"categoria do gabarito achada na fala transcrita: {acertos} de {len(documentos)} frases")
    print(f"gravado em saida/{arquivo}")


def cmd_comparar(args):
    from elo import comparacao
    tabelas_largas()
    comunidade = json.loads((SAIDA / "analise_comunidade.json").read_text(encoding="utf-8"))
    de_campo = json.loads((SAIDA / "analise_campo.json").read_text(encoding="utf-8"))
    tabela, rho = comparacao.comparar(comunidade, de_campo)
    print(tabela.round(1).to_string(index=False))
    print(f"\nρ de Spearman = {comparacao.br(rho, 2)}  (1 = mesma ordem de prioridades; 0 = nenhuma relação)")
    tabela.round(2).to_csv(SAIDA / "comparacao.csv", index=False, encoding="utf-8")
    comparacao.grafico_categorias(tabela, rho, SAIDA / "categorias.png")
    semanal = comparacao.grafico_evolucao(de_campo, SAIDA / "evolucao_campo.png")
    semanal.index = semanal.index.strftime("%Y-%m-%d")          # os números por trás do mapa de calor
    semanal.round(1).to_csv(SAIDA / "evolucao_campo.csv", index_label="semana", encoding="utf-8")
    comparacao.grafico_termos(comunidade["lemas"], "Lemas mais frequentes: comunidade",
                              comparacao.COR["comunidade"], SAIDA / "termos_comunidade.png")
    comparacao.grafico_termos(de_campo["lemas"], "Lemas mais frequentes: campo",
                              comparacao.COR["campo"], SAIDA / "termos_campo.png")
    comparacao.grafico_termos(de_campo["logs"]["achados_valores"]["erro_plataforma"],
                              "Códigos de erro nos logs do motor", comparacao.COR["logs"], SAIDA / "logs.png", 8)
    extras = {}
    if (DADOS / "comunidade.json").exists():
        pacote = coleta.carregar(DADOS / "comunidade.json")
        extras["coleta"] = f"{pacote['coletado_em']}, {pacote['chamadas']} chamadas à API"
        extras.update({f"conferência {k}": f"{v['unicos']}/{v['esperado']} ({'fecha' if v['fecha'] else 'NÃO FECHA'})"
                       for k, v in pacote["conferencias"].items()})
    if (SAIDA / "campo_estatisticas.json").exists():
        extras["máscaras no campo"] = json.loads((SAIDA / "campo_estatisticas.json").read_text(encoding="utf-8"))["mascaras"]
    texto = comparacao.relatorio(tabela, rho, comunidade, de_campo, de_campo["logs"], extras)
    (SAIDA / "relatorio.md").write_text(texto, encoding="utf-8")
    print("gravados em saida/: comparacao.csv, categorias.png, evolucao_campo.png e .csv, termos_*.png, logs.png, relatorio.md")


def cmd_tudo(args):
    if not (args.offline and (DADOS / "comunidade.json").exists()):
        cmd_coletar(args)
    for etapa, extra in ((cmd_campo, {}), (cmd_sintetico, {}), (cmd_analisar, {"corpus": "comunidade"}),
                         (cmd_analisar, {"corpus": "campo"}), (cmd_comparar, {})):
        print(f"\n===== {etapa.__name__[4:]} {extra.get('corpus', '')}")
        etapa(argparse.Namespace(**{**vars(args), **extra}))


def cmd_podcasts(args):
    from elo import coleta_audio
    destino = Path(args.destino)
    if args.conferir:
        pacote = coleta_audio.reconferir(destino, AUDIO)
    else:
        pacote = coleta_audio.coletar(destino, AUDIO, args.max_por_fonte, args.so_listar, args.offline)
    eps = pacote["episodios"]
    if "duracao" in eps[0]:
        print(f"conferência: {sum(e.get('confere', False) for e in eps)} de {len(eps)} episódios conferem; "
              f"{br(sum(e['duracao'] for e in eps) / 3600, 1)} h, {sum(e['bytes'] for e in eps) / 1e6:.0f} MB")
    else:
        print(f"{len(eps)} episódios escolhidos, {br(sum(e['duracao_rss'] for e in eps) / 3600, 1)} h no RSS; "
              f"gravado em {destino}")


def cmd_sintetico_audio(args):
    from elo import sintetico_audio
    pacote = sintetico_audio.gerar(FALA)
    for f in pacote["frases"]:
        print(f"{f['id']} {f['inicio']:6.2f} a {f['fim']:6.2f} s  [{f['categoria']}]  {f['texto']}")
    print(f"pausas inseridas: {', '.join(br(b - a, 1) for a, b in pacote['pausas'])} s")
    print(f"versões em dados/sintetico_falado: {', '.join(v + '.flac' for v in pacote['versoes'])}")


def cmd_sinal(args):
    from elo import sinal
    from elo.coleta_audio import carregar_onda
    if args.corpus == "sintetico-falado":
        gabarito = json.loads((FALA / "gabarito.json").read_text(encoding="utf-8"))
        resultado = {}
        print(f"{'versão':13} {'duração':>8} {'fala':>6} {'pausas':>7} {'inseridas achadas':>18} {'energia':>9} {'zcr':>7}")
        for versao in gabarito["versoes"]:
            onda = carregar_onda(FALA / f"{versao}.flac")
            m = sinal.medir(onda)
            achadas = sinal.pausas(sinal.trechos_de_fala(onda))
            m["inseridas_achadas"] = sum(any(abs(a - p[0]) < 0.06 and abs(b - p[1]) < 0.06 for a, b in achadas)
                                         for p in gabarito["pausas"])
            resultado[versao] = m
            print(f"{versao:13} {m['duracao']:7.1f}s {100 * m['razao_de_fala']:5.0f}% {m['pausas']:7} "
                  f"{m['inseridas_achadas']:>13} de {len(gabarito['pausas'])} {m['energia_db_fala']:7.1f}dB "
                  f"{m['cruzamentos_por_zero']:7.3f}")
        sinal.grafico_onda(carregar_onda(FALA / "limpo.flac"), SAIDA / "onda_sintetico.png",
                           "Sintético falado: a onda e a energia", 30)
        salvar("sinal_sintetico.json", resultado)
        return
    eps = episodios()
    escolhidos = [eps[args.episodio - 1]] if args.episodio else eps
    resultado = {"episodios": {}, "segmentos": {}}
    for ep in escolhidos:
        onda = carregar_onda(AUDIO / f"{ep['id']}.mp3")
        m = sinal.medir(onda)
        resultado["episodios"][ep["id"]] = {"fonte": ep["fonte"], **m}
        print(f"{ep['id']:18} {m['duracao'] / 60:5.1f} min  fala {100 * m['razao_de_fala']:3.0f}%  "
              f"{m['pausas_por_minuto']:5.1f} pausas/min (média {br(m['pausa_media'], 2)} s)  "
              f"energia {br(m['energia_db_fala'])} dB")
        arquivo = TRANSCRICOES / f"{ep['id']}.json"
        if arquivo.exists():
            segmentos = json.loads(arquivo.read_text(encoding="utf-8"))["segmentos"]
            for i, medidas in enumerate(sinal.medir_segmentos(onda, segmentos)):
                resultado["segmentos"][f"{ep['id']}:{i:04d}"] = medidas
    if args.episodio:                         # demonstração: não substitui o arquivo completo
        return
    sinal.grafico_onda(carregar_onda(AUDIO / f"{eps[0]['id']}.mp3", 60, 60), SAIDA / "onda_podcast.png",
                       f"Podcast real: 1 minuto de {eps[0]['titulo'][:48]}...")
    salvar("sinal_podcasts.json", resultado)
    print(f"{len(resultado['segmentos'])} segmentos medidos; gravado em saida/sinal_podcasts.json")


def cmd_transcrever(args):
    from elo import transcricao
    from elo.coleta_audio import carregar_onda
    if args.corpus == "sintetico-falado":
        gabarito = json.loads((FALA / "gabarito.json").read_text(encoding="utf-8"))
        referencia = " ".join(f["texto"] for f in gabarito["frases"])
        resultado = {}
        for versao in gabarito["versoes"]:
            inicio = time.time()
            onda = carregar_onda(FALA / f"{versao}.flac")
            segmentos = transcricao.transcrever(onda, args.modelo)
            hipotese = " ".join(s["texto"] for s in segmentos)
            taxa, s, d, i, n = transcricao.wer(referencia, hipotese)
            resultado[versao] = {"wer": taxa, "trocas": s, "perdidas": d, "inventadas": i, "palavras": n}
            (FALA / f"transcricao_{versao}.json").write_text(json.dumps(
                {"modelo": args.modelo, "segmentos": segmentos}, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"{versao:13} WER {br(100 * taxa)}%  (S {s}, D {d}, I {i} sobre N = {n})  {time.time() - inicio:.1f} s")
        limpo = json.loads((FALA / "transcricao_limpo.json").read_text(encoding="utf-8"))["segmentos"]
        print(f"\nlimpo, como o modelo {args.modelo} ouviu:\n  " + " ".join(s["texto"] for s in limpo))
        salvar(f"wer_sintetico_{args.modelo}.json", resultado)
        return
    eps = episodios()
    if args.trecho:                           # demonstração: um pedaço real, transcrito ao vivo
        ep = eps[(args.episodio or 1) - 1]
        inicio = time.time()
        onda = carregar_onda(AUDIO / f"{ep['id']}.mp3", 60, args.trecho)
        for s in transcricao.transcrever(onda, args.modelo):
            print(f"  [{s['inicio']:5.1f} s] {s['texto']}")
        gasto = time.time() - inicio
        print(f"{ep['titulo'][:70]}: {args.trecho} s transcritos em {gasto:.1f} s ({args.trecho / gasto:.1f}x o tempo real)")
        return
    for i, ep in enumerate(eps, 1):
        print(f"[{i}/{len(eps)}] {ep['id']}")
        transcricao.transcrever_episodio(AUDIO / f"{ep['id']}.mp3", TRANSCRICOES, args.modelo)


def cmd_comparar_audio(args):
    from elo import comparacao_audio as ca
    from elo.coleta_audio import carregar_onda

    def ler(nome):
        return json.loads((SAIDA / nome).read_text(encoding="utf-8"))

    fala, escrita, de_campo = ler("analise_podcasts.json"), ler("analise_comunidade.json"), ler("analise_campo.json")
    tabela, rhos = ca.tres_vias(fala, escrita, de_campo)
    print(tabela[["categoria", "p_fala", "p_escrita", "p_campo", "posicao_fala", "posicao_escrita", "posicao_campo"]]
          .round(1).to_string(index=False))
    for par, rho in rhos.items():
        print(f"ρ {par:16} = {br(rho, 2)}")
    medidas = ler("sinal_podcasts.json")["segmentos"]
    segmentos = [{"categorias": d["categorias"], **medidas[d["id"]]} for d in fala["por_documento"] if d["id"] in medidas]
    ritmo = ca.fala_muda(segmentos)
    print("\nA fala muda quando o assunto é falha? (Mann-Whitney, segmentos com e sem categoria)")
    print(ritmo.round(3).to_string(index=False))
    tabela.round(2).to_csv(SAIDA / "comparacao_audio.csv", index=False, encoding="utf-8")
    salvar("comparacao_audio.json", {"rho": rhos, "categorias": tabela.round(2).reset_index().to_dict("records"),
                                     "fala_muda": ritmo.to_dict("records")})
    ca.grafico_tres(tabela, rhos, SAIDA / "tres_corpus.png")
    ca.grafico_ritmo(segmentos, ritmo, SAIDA / "ritmo.png")
    ca.espectrograma(carregar_onda(FALA / "limpo.flac", 0, 12), SAIDA / "espectrograma.png",
                     "Espectrograma mel do sintético falado: o que o Whisper recebe")
    pacote = json.loads((DADOS / "podcasts.json").read_text(encoding="utf-8"))
    extras = {"fala": f"{len(pacote['episodios'])} episódios, {br(sum(e['duracao'] for e in pacote['episodios']) / 3600, 1)} h, "
                      f"{fala['n_documentos']} segmentos",
              "escrita": f"{escrita['n_documentos']} issues", "campo": f"{de_campo['n_documentos']} blocos do diário"}
    (SAIDA / "relatorio_audio.md").write_text(ca.relatorio(tabela, rhos, ritmo, extras), encoding="utf-8")
    print("gravados em saida/: comparacao_audio.csv, tres_corpus.png, ritmo.png, espectrograma.png, relatorio_audio.md")


MENU1 = [   # etapa 1 (python elo.py etapa1): o roteiro da demonstração
    ("coletar   coleta pequena ao vivo, 20 issues por fonte",
     ["coletar", "--max-por-fonte", "20", "--comentarios", "0", "--destino", "dados/demo.json"]),
    ("campo     diário e logs da integração, só números", ["campo"]),
    ("sintetico os 17 casos sintéticos", ["sintetico"]),
    ("extrair   regex no sintético", ["extrair", "--corpus", "sintetico"]),
    ("extrair   regex no campo", ["extrair", "--corpus", "campo"]),
    ("analisar  spaCy no sintético, token a token do sint-016", ["analisar", "--corpus", "sintetico", "--doc", "sint-016"]),
    ("analisar  spaCy em 100 issues da comunidade", ["analisar", "--corpus", "comunidade", "--limite", "100"]),
    ("comparar  comunidade x campo, gráficos e relatório", ["comparar"]),
]
MENU = [   # etapa 2: o roteiro da demonstração, um número por comando
    ("podcasts      a API da Apple e o RSS ao vivo, sem baixar",
     ["podcasts", "--max-por-fonte", "2", "--so-listar", "--destino", "dados/demo_podcasts.json"]),
    ("podcasts      confere os 20 MP3 baixados", ["podcasts", "--conferir"]),
    ("sintetico     gera as falas sintéticas e os 4 defeitos", ["sintetico-audio"]),
    ("sinal         energia, silêncio e pausas no sintético", ["sinal", "--corpus", "sintetico-falado"]),
    ("transcrever   Whisper tiny no sintético, com WER", ["transcrever", "--corpus", "sintetico-falado", "--modelo", "tiny"]),
    ("extrair       regex na fala transcrita", ["extrair", "--corpus", "sintetico-falado"]),
    ("analisar      spaCy na fala transcrita", ["analisar", "--corpus", "sintetico-falado"]),
    ("transcrever   30 s reais de um podcast, ao vivo", ["transcrever", "--corpus", "podcasts", "--episodio", "1", "--trecho", "30"]),
    ("comparar      fala x escrita x campo; a fala muda?", ["comparar-audio"]),
]


def menu(escolha=None, itens=MENU, etapa=2):
    """Sem comando, o Elo mostra o menu: `python elo.py` pergunta, `python elo.py 3` roda direto.
    O roteiro da etapa 1 continua em `python elo.py etapa1`."""
    while True:
        if escolha is None:
            print(f"\nElo, etapa {etapa}. Escolha um número:")
            for i, (rotulo, _) in enumerate(itens, 1):
                print(f"  {i}  {rotulo}")
            print("  0  sair")
            escolha = input("> ").strip()
        if escolha in ("", "0"):
            return
        if not escolha.isdigit() or not 1 <= int(escolha) <= len(itens):
            print(f"opção inválida: {escolha}")
        else:
            argv = itens[int(escolha) - 1][1]
            print(f"\n$ python elo.py {' '.join(argv)}\n")
            main(argv)
        if not sys.stdin.isatty() or sys.argv[-1].isdigit():   # `python elo.py 3` roda uma vez e sai
            return
        escolha = None


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)   # acento no Windows; log ao vivo
    if argv is None and len(sys.argv) > 1 and sys.argv[1] == "etapa1":
        return menu(sys.argv[2] if len(sys.argv) > 2 else None, MENU1, 1)
    if argv is None and (len(sys.argv) == 1 or sys.argv[1].isdigit()):
        return menu(sys.argv[1] if len(sys.argv) > 1 else None)
    p = argparse.ArgumentParser(prog="elo", description="Elo: integração em texto (etapa 1) e em áudio (etapa 2).")
    p.add_argument("--origem", default=campo.ORIGEM_PADRAO, help="pasta da integração (corpus de campo)")
    sub = p.add_subparsers(dest="comando", required=True)
    s = sub.add_parser("coletar", help="issues do GitHub pela API REST")
    s.add_argument("--max-por-fonte", type=int, default=300)
    s.add_argument("--comentarios", type=int, default=5, help="issues por fonte com comentários lidos")
    s.add_argument("--destino", default=DADOS / "comunidade.json", help="onde gravar (a demo usa dados/demo.json)")
    sub.add_parser("campo", help="diário e logs da integração (só números saem)")
    s = sub.add_parser("sintetico", help="casos sintéticos com os defeitos reais")
    s.add_argument("--n", type=int, default=len(sintetico.SEQUENCIA))
    s.add_argument("--semente", type=int, default=42)
    for nome, ajuda in (("extrair", "expressões regulares sobre um corpus"),
                        ("analisar", "spaCy sobre um corpus")):
        s = sub.add_parser(nome, help=ajuda)
        s.add_argument("--corpus", choices=["comunidade", "campo", "sintetico", "podcasts", "sintetico-falado"],
                       required=True)
        if nome == "extrair":
            s.add_argument("--exemplos", type=int, default=3)
        else:
            s.add_argument("--mostrar", type=int, default=0, help="tabela token a token de N documentos")
            s.add_argument("--doc", help="tabela token a token de um documento pelo id (ex.: sint-016)")
            s.add_argument("--limite", type=int, default=None, help="analisa só os N primeiros")
    sub.add_parser("comparar", help="comunidade x campo: tabela, ρ, gráficos, relatório")
    s = sub.add_parser("tudo", help="a etapa inteira")
    s.add_argument("--offline", action="store_true", help="usa a coleta já gravada")
    s.add_argument("--max-por-fonte", type=int, default=300)
    s.add_argument("--comentarios", type=int, default=5)
    s.add_argument("--n", type=int, default=len(sintetico.SEQUENCIA))
    s.add_argument("--semente", type=int, default=42)
    s.set_defaults(mostrar=0, doc=None, limite=None, destino=DADOS / "comunidade.json")
    s = sub.add_parser("podcasts", help="etapa 2: podcasts pela API da Apple e pelo RSS, MP3 conferidos")
    s.add_argument("--max-por-fonte", type=int, default=6)
    s.add_argument("--so-listar", action="store_true", help="mostra a seleção sem baixar")
    s.add_argument("--conferir", action="store_true", help="confere tamanho e duração do que já baixou")
    s.add_argument("--offline", action="store_true", help="usa a cópia dos feeds gravada")
    s.add_argument("--destino", default=DADOS / "podcasts.json", help="manifesto (a demo usa dados/demo_podcasts.json)")
    sub.add_parser("sintetico-audio", help="etapa 2: falas sintéticas com pausas conhecidas e 4 defeitos")
    for nome, ajuda in (("sinal", "etapa 2: energia, silêncio, pausas e ritmo"),
                        ("transcrever", "etapa 2: faster-whisper e WER")):
        s = sub.add_parser(nome, help=ajuda)
        s.add_argument("--corpus", choices=["podcasts", "sintetico-falado"], required=True)
        s.add_argument("--episodio", type=int, help="só o episódio N do manifesto (demonstração)")
        if nome == "transcrever":
            s.add_argument("--modelo", default="base", choices=["tiny", "base", "small"])
            s.add_argument("--trecho", type=int, help="transcreve só N segundos, ao vivo")
    sub.add_parser("comparar-audio", help="etapa 2: fala x escrita x campo e a fala na falha")
    args = p.parse_args(argv)
    {"coletar": cmd_coletar, "campo": cmd_campo, "sintetico": cmd_sintetico, "extrair": cmd_extrair,
     "analisar": cmd_analisar, "comparar": cmd_comparar, "tudo": cmd_tudo, "podcasts": cmd_podcasts,
     "sintetico-audio": cmd_sintetico_audio, "sinal": cmd_sinal, "transcrever": cmd_transcrever,
     "comparar-audio": cmd_comparar_audio}[args.comando](args)


if __name__ == "__main__":
    main()
