# MiroFish — piloto de Simulação Social

## Função permitida

Explorar reacções sociais e narrativas possíveis face a materiais datados sobre BTC e ETH. A saída é sempre apresentada como **Simulação Social**: cenário exploratório, não previsão de mercado.

## Limites absolutos

- Sem credenciais de corretora, saldo, carteira, alertas ou execução.
- Não cria sinais de compra/venda, preço-alvo ou recomendação financeira.
- Não modifica as regras, posições ou avaliação da estratégia Trend.
- Uma execução só começa com fontes identificadas, uma data de corte e modelo/fornecedor configurado explicitamente.

## Formato auditável de cada execução

Guardar em `research/social-simulations/<id>.json`: fontes e data de corte; actores e pressupostos; cenários alternativos, incluindo o contrário; incertezas; e o aviso **SIMULAÇÃO SOCIAL — NÃO É PREVISÃO NEM SINAL**.

## Teste de utilidade

Antes de qualquer uso recorrente, correr retrospectivamente em eventos conhecidos. Medir se identificou riscos e cenários materiais antes do evento, sem avaliar a qualidade pela eloquência da narrativa. Se não demonstrar utilidade prática repetível, termina-se o piloto.
