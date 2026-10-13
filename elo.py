"""Elo, etapa 1: o que quebra entre dois sistemas, lido em texto.

Cada subcomando chama o módulo de um integrante:
  coletar    Flasio Vinicius   issues do GitHub pela API REST              elo/coleta.py
  campo      Flasio Vinicius   diário e logs da integração, anonimizados   elo/campo.py
  sintetico  Theo Haiek        casos sintéticos com os defeitos reais      elo/sintetico.py
  extrair    Theo Haiek        expressões regulares sobre um corpus        elo/padroes.py
  analisar   Belarmino Neto    spaCy: lemas, sintagmas, entidades          elo/analisador.py
  comparar   Belarmino Neto    comunidade x campo, gráficos e relatório    elo/comparacao.py
  tudo       a equipe          a etapa inteira, de ponta a ponta
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
    documentos, _, _ = campo.ler_diario(args.origem)
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
    analisador = Analisador("en" if args.corpus == "comunidade" else "pt")
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


MENU = [   # o roteiro da demonstração, um número por comando
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


def menu(escolha=None):
    """Sem comando, o Elo mostra o menu: `python elo.py` pergunta, `python elo.py 3` roda direto."""
    while True:
        if escolha is None:
            print("\nElo, etapa 1. Escolha um número:")
            for i, (rotulo, _) in enumerate(MENU, 1):
                print(f"  {i}  {rotulo}")
            print("  0  sair")
            escolha = input("> ").strip()
        if escolha in ("", "0"):
            return
        if not escolha.isdigit() or not 1 <= int(escolha) <= len(MENU):
            print(f"opção inválida: {escolha}")
        else:
            argv = MENU[int(escolha) - 1][1]
            print(f"\n$ python elo.py {' '.join(argv)}\n")
            main(argv)
        if not sys.stdin.isatty() or len(sys.argv) > 1:   # `python elo.py 3` roda uma vez e sai
            return
        escolha = None


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)   # acento no Windows; log ao vivo
    if argv is None and (len(sys.argv) == 1 or sys.argv[1].isdigit()):
        return menu(sys.argv[1] if len(sys.argv) > 1 else None)
    p = argparse.ArgumentParser(prog="elo", description="Elo, etapa 1: problemas de integração em texto.")
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
        s.add_argument("--corpus", choices=["comunidade", "campo", "sintetico"], required=True)
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
    args = p.parse_args(argv)
    {"coletar": cmd_coletar, "campo": cmd_campo, "sintetico": cmd_sintetico, "extrair": cmd_extrair,
     "analisar": cmd_analisar, "comparar": cmd_comparar, "tudo": cmd_tudo}[args.comando](args)


if __name__ == "__main__":
    main()
