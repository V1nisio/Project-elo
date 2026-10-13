# Elo, etapa 1: relatório

- Comunidade: 1278 issues. 243.365 tokens. 64% com alguma categoria
- Campo: 3107 blocos do diário. 107.812 tokens. 40% com alguma categoria
- Logs do motor: 18440 linhas de erro

## Categorias

| categoria | n_comunidade | n_campo | p_comunidade | posicao_comunidade | p_campo | posicao_campo | delta_pp |
|---|---|---|---|---|---|---|---|
| Duplicidade e identidade | 77 | 320 | 5.6 | 7 | 19.1 | 1 | 13.6 |
| Mapeamento de campo e esquema | 221 | 274 | 15.9 | 3 | 16.4 | 2 | 0.4 |
| Ambiente e configuração | 226 | 262 | 16.3 | 2 | 15.7 | 3 | -0.6 |
| Falha silenciosa e divergência | 88 | 223 | 6.3 | 6 | 13.3 | 4 | 7.0 |
| Paginação e leitura em lotes | 54 | 147 | 3.9 | 10 | 8.8 | 5 | 4.9 |
| Autenticação e acesso | 305 | 144 | 22.0 | 1 | 8.6 | 6 | -13.4 |
| Ordem e concorrência | 71 | 107 | 5.1 | 8 | 6.4 | 7 | 1.3 |
| Formato de dado | 154 | 73 | 11.1 | 4 | 4.4 | 8 | -6.7 |
| Rede e disponibilidade | 132 | 72 | 9.5 | 5 | 4.3 | 9 | -5.2 |
| Limite de taxa e cota | 59 | 52 | 4.3 | 9 | 3.1 | 10 | -1.1 |

ρ de Spearman = 0,24. Mais acima no campo do que na comunidade: Duplicidade e identidade (+13,6 p.p.). Mais abaixo: Autenticação e acesso (-13,4 p.p.).

## Termos

- Lemas da comunidade: salesforce (471), error (448), use (326), issue (322), work (308), api (297), create (268), try (263), request (247), add (244), source (239), code (231)
- Sintagmas da comunidade: bulk api (44), source salesforce (44), simple salesforce (40), sync job (36), error message (34), feature request (31), use case (28), salesforce connector (27), salesforce source (24), salesforce object (22), late version (22), sale order (21)
- Lemas do campo (sem nomes próprios): paciente (299), registro (246), linha (234), campo (224), conta (216), agendamento (187), orçamento (185), atendimento (171), carga (169), dia (166), sessão (149), chave (148)
- Sintagmas do campo: chave antigo (17), campo vazio (16), carga noturno (16), escrita direto (14), ciclo seguinte (11), mesmo pessoa (9), carga histórico (8), ciclo manual (7), conta único (7), único exceção (7), produto genérico (7), leitura completo (6)

## O que a máquina gritou (logs)

- Erros de plataforma: CONTA_NAO_CONFIAVEL (2160), REQUIRED_FIELD_MISSING (1284), SEM_CONTA_PAI (541), CONTA_JA_EXISTE_DUPLICATA (243), DUPLICATES_DETECTED (7), NUMBER_OUTSIDE_VALID_RANGE (1)
- Campos customizados: RG_ou_Passapote__c (2568), CE_Procedimentos_Agendados__c (106), Prontuario__c (97), CE_QuantidadeSessoes__c (1)
- HTTP: 500 (145), 503 (1)
- Exceções: ConnectionResetError (33), ConnectTimeoutError (13), NameResolutionError (8), DmlException (8), RemoteException (4)

## Coleta e proteção

- coleta: 2026-10-06T19:34:14+00:00, 45 chamadas à API
- conferência simple-salesforce: 300/300 (fecha)
- conferência jsforce: 300/300 (fecha)
- conferência airbyte: 300/300 (fecha)
- conferência n8n: 59/59 (fecha)
- conferência tap-salesforce: 19/19 (fecha)
- conferência erpnext: 300/300 (fecha)
- máscaras no campo: {'email': 13, 'cpf': 4, 'numero_longo': 31, 'id_sf': 1624, 'segredo': 6, 'telefone': 1}