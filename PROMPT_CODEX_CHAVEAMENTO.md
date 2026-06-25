# PROMPT PARA O CODEX — Sistema de Chaveamento Dinâmico da Copa do Mundo 2026

## Contexto do projeto

Estou criando um dashboard em HTML, CSS e JavaScript para acompanhar a Copa do Mundo 2026.

Quero implementar no meu dashboard um sistema de chaveamento de mata-mata, inspirado em uma imagem de referência com visual de estádio, linhas luminosas e confrontos em formato de chaveamento.

## Atenção principal

Não quero uma imagem estática.

Quero um componente funcional, dinâmico e orientado por dados, feito em HTML, CSS e JavaScript.

O chaveamento deve ir sendo preenchido ao longo do tempo conforme os resultados dos jogos forem cadastrados.

Prioridade máxima: o chaveamento precisa ser orientado por dados, não desenhado manualmente. Cada card de jogo deve ser gerado a partir de um objeto JavaScript, porque os resultados da Copa vão mudar ao longo do tempo.

---

## Objetivo geral

Criar uma seção de chaveamento no dashboard onde os confrontos do mata-mata sejam exibidos e atualizados automaticamente.

O sistema deve permitir:

- visualizar as fases do mata-mata;
- cadastrar ou editar resultados;
- identificar automaticamente o vencedor;
- avançar o vencedor para a próxima fase;
- salvar os dados no navegador;
- manter os dados salvos mesmo após fechar e abrir novamente o dashboard.

---

## Estrutura visual desejada

Criar um chaveamento visual de mata-mata com as seguintes fases:

- Oitavas de final;
- Quartas de final;
- Semifinal;
- Final;
- Campeão.

Cada confronto deve ter dois times.

Cada time deve mostrar:

- nome do país;
- bandeira ou emoji da bandeira;
- placar;
- pênaltis, quando necessário;
- status do jogo.

Os confrontos futuros devem aparecer como:

- `A definir`;
- placar vazio;
- status `aguardando classificados`.

---

## Funcionamento dinâmico

O chaveamento deve funcionar da seguinte forma:

1. O usuário informa ou altera o placar de uma partida.
2. O sistema verifica se a partida foi finalizada.
3. O sistema identifica o vencedor pelo placar.
4. Se houver empate, o sistema deve usar os pênaltis ou permitir escolha manual do classificado.
5. O vencedor é enviado automaticamente para o confronto correto da próxima fase.
6. O chaveamento é renderizado novamente na tela.
7. Os dados são salvos no `localStorage`.

Fluxo principal:

```text
resultado do jogo -> identifica vencedor -> preenche próxima fase -> salva no navegador -> atualiza o dashboard
```

---

## Estrutura de dados JavaScript sugerida

Use uma estrutura parecida com esta, podendo adaptar conforme a arquitetura do projeto:

```javascript
const bracketData = {
  roundOf16: [
    {
      id: "oitavas-1",
      round: "Oitavas de final",
      teamA: {
        name: "Brasil",
        flag: "🇧🇷",
        score: null,
        penalties: null
      },
      teamB: {
        name: "Uruguai",
        flag: "🇺🇾",
        score: null,
        penalties: null
      },
      winnerNextMatchId: "quartas-1",
      winnerSlot: "teamA",
      status: "scheduled",
      winner: null
    }
  ],

  quarterFinals: [
    {
      id: "quartas-1",
      round: "Quartas de final",
      teamA: null,
      teamB: null,
      winnerNextMatchId: "semifinal-1",
      winnerSlot: "teamA",
      status: "waiting",
      winner: null
    }
  ],

  semiFinals: [
    {
      id: "semifinal-1",
      round: "Semifinal",
      teamA: null,
      teamB: null,
      winnerNextMatchId: "final-1",
      winnerSlot: "teamA",
      status: "waiting",
      winner: null
    }
  ],

  final: [
    {
      id: "final-1",
      round: "Final",
      teamA: null,
      teamB: null,
      winnerNextMatchId: null,
      winnerSlot: null,
      status: "waiting",
      winner: null
    }
  ],

  champion: null
};
```

---

## Funções JavaScript obrigatórias

Criar funções para:

### Renderização

- `renderBracket()`
  - Renderiza todas as fases do chaveamento na tela.
  - Cria os cards dos jogos dinamicamente.
  - Atualiza os confrontos quando os dados mudarem.

### Atualização de placar

- `updateMatchScore(matchId, teamAScore, teamBScore, teamAPenalties, teamBPenalties)`
  - Atualiza o placar de uma partida.
  - Atualiza os pênaltis quando houver empate.
  - Salva os dados.

### Identificação de vencedor

- `getMatchWinner(match)`
  - Retorna o time vencedor.
  - Usa o placar normal quando houver vencedor no tempo normal.
  - Usa pênaltis quando o placar normal estiver empatado.
  - Se ainda não for possível definir vencedor, retorna `null`.

### Avanço de fase

- `advanceWinner(match)`
  - Envia o vencedor para o confronto correto da próxima fase.
  - Usa `winnerNextMatchId` e `winnerSlot`.
  - Se for a final, define o campeão.

### Persistência

- `saveBracketData()`
  - Salva o chaveamento no `localStorage`.

- `loadBracketData()`
  - Carrega o chaveamento salvo ao abrir o dashboard.

### Reset

- `resetBracket()`
  - Limpa os resultados e volta o chaveamento para o estado inicial.
  - Pedir confirmação antes de apagar.

---

## Campos editáveis no card do jogo

Cada card de confronto deve permitir:

- editar placar do time A;
- editar placar do time B;
- editar pênaltis do time A, se necessário;
- editar pênaltis do time B, se necessário;
- marcar o jogo como:
  - agendado;
  - em andamento;
  - finalizado;
  - aguardando classificados;
- botão para salvar resultado;
- botão para limpar resultado daquele jogo.

---

## Regras de classificação

### Vitória no tempo normal

Se o placar for:

```text
Brasil 2 x 0 Uruguai
```

Brasil avança automaticamente.

### Empate com pênaltis

Se o placar for:

```text
Brasil 1 x 1 Uruguai
Pênaltis: Brasil 4 x 3 Uruguai
```

Brasil avança automaticamente.

### Empate sem pênaltis

Se o placar for:

```text
Brasil 1 x 1 Uruguai
```

O sistema não deve avançar ninguém ainda.

Nesse caso, mostrar aviso:

```text
Empate detectado. Informe os pênaltis ou selecione manualmente o classificado.
```

---

## Visual desejado

Criar um visual moderno, escuro, tecnológico e esportivo.

Referência estética:

- fundo escuro;
- cards com bordas luminosas;
- linhas conectando as fases;
- efeito neon azul;
- aparência de painel esportivo;
- estilo inspirado em estádio e Copa do Mundo;
- organização limpa;
- sem poluir a tela.

Características visuais:

- usar tons escuros no fundo;
- usar brilho azul nas bordas;
- usar sombra leve nos cards;
- destacar vencedor;
- deixar jogos aguardando em visual mais apagado;
- usar layout horizontal no desktop;
- usar layout vertical ou com rolagem no celular;
- manter boa leitura em telas menores.

---

## Responsividade

O componente deve funcionar bem em:

- desktop;
- notebook;
- tablet;
- celular.

No desktop, o chaveamento pode ser horizontal:

```text
Oitavas -> Quartas -> Semifinal -> Final -> Campeão
```

No celular, pode ser vertical ou com rolagem horizontal controlada.

---

## Integração com o dashboard atual

Antes de codificar, analise a estrutura atual do projeto.

Identifique:

- arquivo HTML principal;
- arquivo CSS principal;
- arquivo JavaScript principal;
- onde está a tabela de classificação;
- onde a nova seção de chaveamento deve entrar.

Não quebre a tabela de classificação existente.

A nova seção deve ser adicionada sem prejudicar o restante do dashboard.

Se possível, criar arquivos separados:

```text
bracket.html
bracket.css
bracket.js
```

Ou, se a estrutura atual for simples, adicionar:

- a seção no `index.html`;
- os estilos no CSS atual;
- a lógica no JavaScript atual.

Escolha a forma mais organizada para o projeto.

---

## Resultado esperado

Ao final, quero conseguir:

1. Abrir o dashboard no navegador.
2. Ver a seção de chaveamento.
3. Ver os confrontos das oitavas, quartas, semifinal, final e campeão.
4. Inserir ou alterar resultados.
5. Ver o vencedor avançar automaticamente.
6. Resolver empates com pênaltis.
7. Fechar e abrir o navegador mantendo os dados salvos.
8. Resetar o chaveamento quando necessário.

---

## Cuidados importantes

- Não usar imagem fixa como chaveamento.
- Não desenhar os confrontos manualmente no HTML.
- Não duplicar lógica desnecessária.
- Não quebrar a tabela de classificação atual.
- Não remover funcionalidades já existentes.
- Não criar código confuso ou difícil de manter.
- Manter HTML, CSS e JavaScript bem organizados.
- Comentar as partes principais do código para facilitar meu aprendizado.

---

## Antes de implementar

Antes de alterar qualquer arquivo, faça o seguinte:

1. Analise a estrutura atual do projeto.
2. Me diga quais arquivos existem.
3. Me diga quais arquivos você pretende modificar.
4. Me diga se será necessário criar novos arquivos.
5. Só depois implemente a solução.

---

## Entrega esperada

Depois da implementação, explique:

- quais arquivos foram alterados;
- quais arquivos foram criados;
- como testar o chaveamento;
- como cadastrar resultados;
- como resetar os dados;
- onde fica salvo o estado do chaveamento;
- como adaptar os confrontos reais quando eles forem definidos.
