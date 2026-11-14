# Elo, etapa 2: relatório da fala

- fala: 20 episódios, 14,0 h, 12213 segmentos
- escrita: 1278 issues
- campo: 3107 blocos do diário

## H1: as três ordens

| categoria | n_fala | n_escrita | n_campo | p_fala | posicao_fala | p_escrita | posicao_escrita | p_campo | posicao_campo |
|---|---|---|---|---|---|---|---|---|---|
| Ambiente e configuração | 157 | 226 | 262 | 30.6 | 1 | 16.3 | 2 | 15.7 | 3 |
| Autenticação e acesso | 106 | 305 | 144 | 20.7 | 2 | 22.0 | 1 | 8.6 | 6 |
| Mapeamento de campo e esquema | 79 | 221 | 274 | 15.4 | 3 | 15.9 | 3 | 16.4 | 2 |
| Formato de dado | 68 | 154 | 73 | 13.3 | 4 | 11.1 | 4 | 4.4 | 8 |
| Rede e disponibilidade | 38 | 132 | 72 | 7.4 | 5 | 9.5 | 5 | 4.3 | 9 |
| Ordem e concorrência | 36 | 71 | 107 | 7.0 | 6 | 5.1 | 8 | 6.4 | 7 |
| Falha silenciosa e divergência | 12 | 88 | 223 | 2.3 | 7 | 6.3 | 6 | 13.3 | 4 |
| Duplicidade e identidade | 10 | 77 | 320 | 1.9 | 8 | 5.6 | 7 | 19.1 | 1 |
| Paginação e leitura em lotes | 5 | 54 | 147 | 1.0 | 9 | 3.9 | 10 | 8.8 | 5 |
| Limite de taxa e cota | 2 | 59 | 52 | 0.4 | 10 | 4.3 | 9 | 3.1 | 10 |

- ρ fala x escrita = 0,94
- ρ fala x campo = 0,22
- ρ escrita x campo = 0,24

## H2: a fala muda quando o assunto é falha?

| medida | mediana_com_falha | mediana_sem_falha | n_com | n_sem | U | p | efeito_r |
|---|---|---|---|---|---|---|---|
| palavras por minuto | 190.0 | 198.3 | 487 | 10367 | 2326255.0 | 0.0034 | 0.0785 |
| pausa antes (s) | 0.06 | 0.08 | 503 | 11690 | 2632554.0 | 0.0001 | 0.1046 |
| energia (dB) | -20.9 | -21.7 | 503 | 11710 | 3111425.5 | 0.0317 | -0.0565 |