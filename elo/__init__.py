"""Elo: um analisador do que quebra entre dois sistemas que precisam conversar.

Etapa 1 (texto): coleta por web API (GitHub), expressões regulares e spaCy.
O caso real é a integração ModernaNet (ERP da clínica) x Salesforce (CRM),
em produção desde 15/09/2026.
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"
SAIDA = RAIZ / "saida"

EQUIPE = {
    "Flasio Vinicius": ["elo/coleta.py", "elo/campo.py", "elo/coleta_audio.py"],
    "Theo Haiek": ["elo/padroes.py", "elo/sintetico.py", "elo/sinal.py", "elo/sintetico_audio.py"],
    "Belarmino Neto": ["elo/analisador.py", "elo/comparacao.py", "elo/transcricao.py", "elo/comparacao_audio.py"],
}
