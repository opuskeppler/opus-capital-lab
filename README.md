# OPUS Crypto Paper Lab

Simulação auditável de uma carteira de €200 com preços reais, sem ligação a corretoras, API keys ou capital real.

## Mandato de teste

- Capital inicial: €200
- Horizonte: 12 meses
- Objectivo aspiracional: €400, sem promessa de retorno
- Universo inicial: Bitcoin (BTC) e Ethereum (ETH)
- Custos simulados: 0,20% por operação
- Sem alavancagem, derivados, short selling ou execução automática real

O simulador avalia diariamente a tendência de cada activo por médias móveis de 20 e 60 dias. A carteira só assume exposição quando a tendência é positiva; mantém caixa se não houver sinal. Cada decisão e operação fica guardada em `logs/ledger.jsonl`.

## Executar

```bash
python3 simulator.py
```

O script consulta cotações públicas da CoinGecko, actualiza `data/state.json` e imprime um resumo. Se a API não estiver disponível, não altera a carteira.

## Critérios de avaliação

O teste não será aprovado apenas por lucro. A avaliação inclui retorno líquido, drawdown máximo, exposição, custos, número de operações e comportamento em períodos de queda. O capital real só poderá ser considerado depois de evidência consistente e de aprovação manual do Rodd para cada ordem.
