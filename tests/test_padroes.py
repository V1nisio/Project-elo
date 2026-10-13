"""Testes das expressões regulares e das fórmulas de verificação (padroes.py)."""
import random

from elo.padroes import (anonimizar, classificar_cpf, cpf_valido, digitos_verificadores,
                         extrair, sinais_de_categoria, sufixo_id_sf)
from elo.sintetico import cpf_deslocado, gerar, novo_cpf


def tipos(texto):
    return [(a.tipo, a.valor) for a in extrair(texto)]


def test_dv_do_cpf_pela_formula():
    assert digitos_verificadores("529982247") == "25"
    assert cpf_valido("52998224725")
    assert not cpf_valido("52998224724")
    assert not cpf_valido("11111111111")          # todos iguais fecham o DV, mas não valem


def test_cpf_machucado_como_a_integracao_viu():
    rng = random.Random(1)
    com_zero = novo_cpf(rng, com_zero=True)
    assert classificar_cpf(str(int(com_zero))) == "sem_zero"
    assert classificar_cpf(cpf_deslocado(rng)) == "deslocado"
    assert classificar_cpf("529.982.247-25") == "valido"
    assert classificar_cpf("12345") == "invalido"


def test_sufixo_do_id_salesforce():
    assert sufixo_id_sf("001A0000006Vm9r") == "IAC"
    assert ("id_sf", "001A0000006Vm9rIAC") in tipos("conta 001A0000006Vm9rIAC criada")
    assert not any(t == "id_sf" for t, _ in tipos("conta 001A0000006Vm9rXXX criada"))


def test_http_so_com_contexto_e_sem_duplicar():
    assert tipos("HTTP 429 Too Many Requests") == [("http", "429")]
    assert not any(t == "http" for t, _ in tipos("a varredura trouxe 500 linhas"))
    assert ("http", "401") in tipos('{"statusCode":401}')


def test_erro_de_plataforma_contra_coluna():
    achados = dict(tipos("REQUIRED_FIELD_MISSING em STATUS_AGENDAMENTO"))
    assert achados["erro_plataforma"] == "REQUIRED_FIELD_MISSING"
    assert achados["identificador"] == "STATUS_AGENDAMENTO"


def test_regressoes_achadas_na_coleta_real():
    # o marcador do próprio anonimizador não é identificador; SalesforceLogin é função
    assert tipos("Account <ID_SF> None: REQUIRED_FIELD_MISSING") == [("erro_plataforma", "REQUIRED_FIELD_MISSING")]
    assert tipos("import SalesforceLogin; raise SalesforceExpiredSession") == [("excecao", "SalesforceExpiredSession")]
    limpo, _ = anonimizar("telefone 99999999999, e-mail")       # vírgula de pontuação depois do número
    assert "<NUM>," in limpo


def test_campo_customizado_com_objeto():
    (achado,) = [a for a in extrair("Account.PacienteID_Moderna__c é único") if a.tipo == "campo_custom"]
    assert (achado.valor, achado.detalhe) == ("PacienteID_Moderna__c", "Account")


def test_retrovisor_do_nome_repetido():
    assert ("nome_repetido", "Marina Marina") in tipos("Cadastro: Marina Marina Duarte")
    assert not any(t == "nome_repetido" for t, _ in tipos("Ana Maria Duarte"))


def test_anonimizar_tira_segredo_cpf_email_e_telefone():
    falso = str(int(novo_cpf(random.Random(3), com_zero=True)))      # CPF sintético sem o zero
    texto = ("client_secret=0123456789abcdef0123456789abcdef01234567 CPF 529.982.247-25 "
             f"mail fulano@exemplo.com tel (11) 98765-4321 e {falso}")
    limpo, contagem = anonimizar(texto)
    assert "0123456789abcdef" not in limpo and "529.982" not in limpo and "@" not in limpo
    assert "98765" not in limpo and falso not in limpo
    assert contagem["segredo"] == 1 and contagem["cpf"] == 1 and contagem["numero_longo"] == 1


def test_sinais_viram_categorias():
    texto = "HTTP 429; REQUIRED_FIELD_MISSING; DUPLICATE_VALUE; ConnectionResetError; ?offset=1000"
    assert sinais_de_categoria(extrair(texto)) == {"limite_taxa", "mapeamento", "duplicidade", "rede", "paginacao"}


def test_sintetico_e_reprodutivel_e_cobre_todos_os_defeitos():
    a, b = gerar(semente=7), gerar(semente=7)
    assert a == b
    assert sum(d["defeito"] == "cpf_repetido" for d in a) == 2
