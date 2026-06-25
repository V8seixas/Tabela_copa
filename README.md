# Tabela da Copa 2026

App em Python para acompanhar resultados recentes, proximos jogos e a tabela dos
grupos da Copa do Mundo FIFA 2026 em formato de dashboard no terminal.

Os dados sao buscados do placar publico da ESPN para a liga `fifa.world`:

<https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard>

## Como usar

```bash
python3 copa2026.py
```

A tela mostra cards de resumo, proximas etapas do torneio, tabela dos grupos,
proximos jogos e resultados recentes.

Mostrar apenas um grupo:

```bash
python3 copa2026.py --grupo K
```

Atualizar automaticamente a cada 60 segundos:

```bash
python3 copa2026.py --watch 60
```

Gerar um arquivo HTML para abrir no navegador:

```bash
python3 copa2026.py --html dashboard.html
```

O HTML gerado exibe `Autor: Vinícius Melo Seixas`.

O dashboard tambem inclui um chaveamento visual do mata-mata, com fase de 32,
oitavas, quartas, semifinais, final e campeao. Os confrontos sao montados
automaticamente a partir dos dados da ESPN.

Exportar os dados normalizados em JSON:

```bash
python3 copa2026.py --json
```

O JSON tambem inclui o campo `stage` em cada partida para identificar fase de
grupos, fase de 32, oitavas, quartas, semifinais, disputa de 3o lugar ou final.

Consultar um periodo especifico:

```bash
python3 copa2026.py --inicio 2026-06-11 --data 2026-06-24
```

## Observacoes

- Nao precisa instalar bibliotecas externas.
- O app cria um cache em `.cache/copa2026-scoreboard.json` e usa esse arquivo se
  a internet falhar.
- A classificacao usa os criterios disponiveis no placar: pontos, saldo de gols
  e gols marcados. Se ainda persistir empate, os nomes sao usados apenas para
  manter uma ordem estavel na tela.

## Testes

```bash
python3 -m unittest
```
