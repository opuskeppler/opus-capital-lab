# OPUS Crypto Paper Lab

Simulação auditável de uma carteira de €200 com preços reais, sem ligação a corretoras, API keys ou capital real.

## Mandato de teste

- Capital inicial: €200
- Horizonte: 12 meses
- Objectivo aspiracional: €400, sem promessa de retorno
- Universo inicial: Bitcoin (BTC) e Ethereum (ETH)
- Custos simulados: 0,20% por operação
- Sem alavancagem, derivados, short selling ou execução automática real

O simulador avalia a tendência de cada activo a cada três minutos por médias móveis de 20 e 60 dias. A carteira só assume exposição quando a tendência é positiva; mantém caixa se não houver sinal. Cada decisão e operação fica guardada em `logs/ledger.jsonl`. A passagem de cada ciclo não força uma operação: só compra ou vende quando as regras o justificam.

## MiroFish — Simulação Social

O painel inclui um piloto isolado de **Simulação Social** com MiroFish. Serve para explorar cenários e reacções de actores a materiais datados; não prevê preços, não emite sinais e não tem qualquer acesso à carteira ou às regras da Trend. As salvaguardas e o formato de auditoria estão em [`MIROFISH_PILOT.md`](MIROFISH_PILOT.md).

## Executar

```bash
python3 simulator.py
```

O script consulta cotações públicas da CoinGecko, actualiza `data/state.json` e imprime um resumo. Se a API não estiver disponível, não altera a carteira.

## Critérios de avaliação

O teste não será aprovado apenas por lucro. A avaliação inclui retorno líquido, drawdown máximo, exposição, custos, número de operações e comportamento em períodos de queda. O capital real só poderá ser considerado depois de evidência consistente e de aprovação manual do Rodd para cada ordem.
