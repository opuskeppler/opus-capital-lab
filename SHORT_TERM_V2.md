# Short-term v2 — investigação e critérios de prova

## Decisão de desenho

O modelo 5/15 foi descontinuado como estratégia candidata: num mercado com
custos, este horizonte é dominado por ruído e por mudanças rápidas de regime.
O v2 não tenta adivinhar o preço exacto. Estima a probabilidade de um retorno
positivo nas próximas 24 horas e só admite exposição quando vários sinais
independentes concordam.

## Factores do modelo

1. **Regime/tendência** — preço acima das médias de 12 e 48 horas.
2. **Momentum** — retornos de 4h e 24h positivos, sem procurar reversões
   contra uma tendência forte.
3. **Volatilidade** — volatilidade realizada das últimas 24h comparada com a
   janela de 30 dias. Volatilidade anormal reduz a posição ou bloqueia entrada.
4. **Participação** — volume das últimas 24h face à média semanal.
5. **Sentimento** — Fear & Greed é filtro de extremo, nunca gatilho isolado.
6. **Notícias** — manchetes com risco operacional/regulatório suspendem novas
   entradas até revisão do evento.

## Regras propostas para a versão paper

- Avaliação de hora a hora, não a cada três minutos.
- Entrada somente com tendência positiva, momentum positivo e confiança
  calibrada >= 65%.
- Risco por posição limitado a 0,5% do valor da carteira; tamanho calculado a
  partir da volatilidade, nunca por percentagem fixa arbitrária.
- Exposição agregada máxima de 60%; BTC e ETH não contam como diversificação
  plena em choques de mercado.
- Stop baseado em volatilidade e validade máxima de 24 horas. Sem média de
  preço para baixo, sem alavancagem e sem short.
- Pausa diária a -2% e pausa total a -5% desde o pico; reentrada exige novo
  dia e novo sinal, não uma tentativa automática de recuperar perdas.

## Como validar antes de a promover

1. Construir histórico horário de pelo menos 24 meses, incluindo custos,
   spread estimado e slippage.
2. Fazer validação walk-forward: calibrar apenas no passado e testar no bloco
   seguinte, sem reutilizar os dados de teste.
3. Comparar com BTC buy-and-hold, ETH buy-and-hold e ficar em caixa.
4. Exigir retorno líquido superior ao benchmark, drawdown inferior e um número
   razoável de operações durante pelo menos 90 dias de shadow mode.
5. Só então substituir o simulador actual; capital real continua explicitamente
   fora de âmbito.

O conjunto horário de 24 meses é recolhido e validado localmente por
`download_history.py`; cada ficheiro inclui abertura, máximo, mínimo, fecho,
volume e número de transacções, e o manifesto assinala qualquer lacuna.

## Leituras que sustentam o desenho

- CoinGecko documenta que o endpoint histórico devolve dados horários em
  janelas de 2–90 dias; é a base actual de preços/volume.
- A literatura de previsão de crypto alerta que resultados de aprendizagem de
  máquina desaparecem frequentemente fora da amostra e depois de custos. Por
  isso, o v2 começa por factores explicáveis e validação walk-forward, em vez
  de uma rede neuronal opaca.
- Estudos de volatilidade em crypto encontram utilidade em prever
  volatilidade; aqui ela é usada principalmente para dimensionar e limitar
  risco, onde é mais defensável do que prever retornos pontuais.

## Fontes activas

Ver `research/sources.json`. O primeiro snapshot pode ser criado com:

```bash
python3 research_pipeline.py
```

O ficheiro gerado é deliberadamente separado do ledger e do estado de carteira.

Para calcular a recomendação explicável em shadow mode:

```bash
python3 strategy_v2.py
```

O resultado é guardado em `data/short-term-v2-shadow.json` e não altera a
simulação actual.
