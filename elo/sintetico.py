"""Casos sintéticos para a execução ao vivo.

Responsável: Theo Haiek.

Nenhum dado real entra aqui. Os nomes são sorteados de listas, os CPFs são
gerados pelo próprio dígito verificador e os ids do Salesforce ganham o sufixo
calculado. Mas cada linha carrega um defeito de formato que a integração
ModernaNet x Salesforce encontrou de verdade, com o número medido lá.
"""
import random
import string

from .padroes import cpf_valido, digitos_verificadores, sufixo_id_sf

NOMES = ["Ana", "Bruno", "Carla", "Diego", "Elisa", "Fábio", "Gisele", "Heitor", "Iara",
         "Joana", "Lívia", "Marcos", "Marina", "Nina", "Otávio", "Paula", "Rafael", "Sofia"]
SOBRENOMES = ["Almeida", "Barbosa", "Cardoso", "Duarte", "Esteves", "Ferraz", "Gomes",
              "Lacerda", "Macedo", "Nogueira", "Pires", "Queiroz", "Rezende", "Teixeira"]


def novo_cpf(rng, com_zero=False):
    """CPF válido de verdade: 9 dígitos sorteados mais os dois DVs calculados."""
    primeiro = "0" if com_zero else str(rng.randint(1, 9))
    nove = primeiro + "".join(rng.choice(string.digits) for _ in range(8))
    return nove + digitos_verificadores(nove)


def com_mascara(cpf):
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"


def cpf_deslocado(rng):
    """CPF que começava com zero, com o zero migrado para o fim, e que NÃO fecha
    o DV sozinho (para o exemplo da demonstração ser inequívoco)."""
    while True:
        errado = novo_cpf(rng, com_zero=True)[1:] + "0"
        if not cpf_valido(errado):
            return errado


def novo_id_sf(rng, prefixo="001"):
    corpo = prefixo + "".join(rng.choice(string.ascii_letters + string.digits) for _ in range(12))
    return corpo + sufixo_id_sf(corpo)


def nome(rng):
    return f"{rng.choice(NOMES)} {rng.choice(SOBRENOMES)}"


def nome_com_repeticao(rng):
    primeiro = rng.choice(NOMES)
    return f"{primeiro} {primeiro} {rng.choice(SOBRENOMES)}"


# Cada defeito escreve uma linha. ctx guarda o que precisa se repetir entre linhas.
DEFEITOS = {
    "cpf_valido": lambda rng, ctx: f"Paciente {nome(rng)} cadastrado com CPF {com_mascara(novo_cpf(rng))}.",
    "cpf_sem_zero": lambda rng, ctx: (f"Paciente {nome(rng)} chegou com CPF "
                                      f"{int(novo_cpf(rng, com_zero=True))} (a origem converteu para número)."),
    "cpf_deslocado": lambda rng, ctx: f"Paciente {nome(rng)} com CPF {cpf_deslocado(rng)} no cadastro.",
    "cpf_repetido": lambda rng, ctx: f"Paciente {nome(rng)} cadastrado com CPF {com_mascara(ctx['cpf_repetido'])}.",
    "nome_repetido": lambda rng, ctx: f"Cadastro novo: {nome_com_repeticao(rng)}, sem prontuário.",
    "preenchimento": lambda rng, ctx: f"Contato de {nome(rng)}: telefone 99999999999, e-mail nao@gmail.com.",
    "telefone": lambda rng, ctx: (f"Retorno pedido por {nome(rng)} no ({rng.randint(11, 99)}) "
                                  f"9{rng.randint(1000, 9999)}-{rng.randint(1000, 9999)}."),
    "tres_formatos": lambda rng, ctx: ("DATA_AGENDAMENTO 2026-08-04T00:00:00, DATA_ATENDIMENTO 05/06/2026 e "
                                       "DATAPARAM 20260910: três formatos de data na mesma API."),
    "campo_obrigatorio": lambda rng, ctx: (f"[06/10 23:15:02] Account {novo_id_sf(rng)} None: REQUIRED_FIELD_MISSING: "
                                           f"Campos obrigatórios ausentes: [RG_ou_Passapote__c]"),
    "duplicata": lambda rng, ctx: (f"Opportunity.C_digo__c recusou a segunda cópia de "
                                   f"MOD-ORC-{rng.randint(100, 9999)}: DUPLICATE_VALUE"),
    "conta_pai": lambda rng, ctx: (f"2026-10-06 23:16:40,120 ERROR não confirmado: MOD-AGD-{rng.randint(1500000, 1950000)}"
                                   f"-{rng.randint(70000, 80000)}, SEM_CONTA_PAI: a conta ainda não existe"),
    "http_500": lambda rng, ctx: (f"[06/10 23:17:00] HTTP 500 ao ler /api/v2/Moderna/Busca?consulta=PACIENTES"
                                  f"&limit=1000&offset={rng.choice([0, 1000, 2000])}"),
    "http_429": lambda rng, ctx: "[06/10 23:18:30] HTTP 429 Too Many Requests: aguardando 20 s (Retry-After)",
    "rede": lambda rng, ctx: ("erro no ciclo: HTTPSConnectionPool(host='exemplo.my.salesforce.com', port=443): "
                              "Max retries exceeded (Caused by NameResolutionError)"),
    "segredo": lambda rng, ctx: ('curl -d "grant_type=client_credentials&client_secret='
                                 + "".join(rng.choice("0123456789abcdef") for _ in range(64)) + '"'),
    "falha_silenciosa": lambda rng, ctx: (f"A gravação devolveu 200, mas MOD-ATD-2026-1-{rng.randint(100, 999)} "
                                          f"não apareceu na releitura: falhou sem erro."),
}
# cpf_repetido entra de novo no fim: o mesmo CPF válido em duas pessoas (139 casos reais).
SEQUENCIA = [*DEFEITOS, "cpf_repetido"]


def gerar(n=len(SEQUENCIA), semente=42):
    """n linhas sintéticas, sempre as mesmas para a mesma semente."""
    rng = random.Random(semente)
    ctx = {"cpf_repetido": novo_cpf(rng)}
    documentos = []
    for i in range(n):
        defeito = SEQUENCIA[i % len(SEQUENCIA)]
        documentos.append({"id": f"sint-{i + 1:03d}", "fonte": "sintetico", "defeito": defeito,
                           "prosa": DEFEITOS[defeito](rng, ctx), "codigo": ""})
    return documentos
