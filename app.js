const money = new Intl.NumberFormat('pt-PT', { style: 'currency', currency: 'EUR' });
const pct = value => `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
const assetIds = ['bitcoin', 'ethereum'];
let dashboard;

function currentPrices() {
  return fetch('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=eur', { cache: 'no-store' })
    .then(response => response.ok ? response.json() : Promise.reject(new Error('Mercado indisponível')));
}

function readLedger() {
  return fetch('logs/ledger.jsonl', { cache: 'no-store' })
    .then(response => response.ok ? response.text() : '')
    .then(text => text.trim().split('\n').filter(Boolean).map(line => JSON.parse(line)));
}

function drawChart(entries) {
  const values = entries.length ? entries.map(entry => entry.portfolio_value_eur) : [200];
  if (values.length === 1) values.push(values[0]);
  const min = Math.min(...values, 195), max = Math.max(...values, 205), range = max - min || 1;
  const points = values.map((value, index) => `${(index / (values.length - 1)) * 700},${156 - ((value - min) / range) * 112}`).join(' ');
  document.querySelector('#chart-line').setAttribute('d', `M ${points.replace(' ', ' L ')}`);
  document.querySelector('#chart-fill').setAttribute('d', `M 0,156 L ${points.replace(' ', ' L ')} L 700,156 Z`);
}

function renderLedger(entries) {
  const rows = entries.slice(-6).reverse();
  document.querySelector('#operations-count').textContent = `${entries.reduce((sum, item) => sum + item.operations.length, 0)} operações`;
  document.querySelector('#ledger').innerHTML = rows.length ? rows.map(entry => {
    const ops = entry.operations.length ? entry.operations.map(op => `${op.side} ${dashboard.config.assets[op.asset].symbol} · ${money.format(op.eur)}`).join(' / ') : 'Sem operação — regra diária mantida';
    return `<div class="ledger-row"><time>${new Date(entry.timestamp).toLocaleString('pt-PT', {dateStyle:'medium', timeStyle:'short'})}</time><span>${ops}</span><b>${pct(entry.return_pct)}</b></div>`;
  }).join('') : '<div class="ledger-row"><span>A aguardar o primeiro registo.</span></div>';
  drawChart(entries);
}

function render(prices, entries) {
  const { config, state, snapshot } = dashboard;
  const holdingsValue = assetIds.reduce((sum, asset) => sum + state.holdings[asset] * prices[asset].eur, 0);
  const portfolio = state.cash_eur + holdingsValue;
  const returnPct = (portfolio / config.starting_capital_eur - 1) * 100;
  const targetProgress = Math.max(0, ((portfolio - config.starting_capital_eur) / (config.target_capital_eur - config.starting_capital_eur)) * 100);
  const active = !snapshot.risk_pause;
  document.querySelector('#portfolio-value').textContent = money.format(portfolio);
  document.querySelector('#portfolio-return').textContent = `${pct(returnPct)} desde o início`;
  document.querySelector('#target-progress').textContent = `${targetProgress.toFixed(1)}%`;
  document.querySelector('#cash-value').textContent = money.format(state.cash_eur);
  document.querySelector('#cash-weight').textContent = `${(state.cash_eur / portfolio * 100).toFixed(1)}% em caixa`;
  document.querySelector('#drawdown').textContent = `${(state.max_drawdown * 100).toFixed(2)}%`;
  document.querySelector('#updated').textContent = `PREÇOS · ${new Date().toLocaleTimeString('pt-PT',{hour:'2-digit',minute:'2-digit'})}`;
  document.querySelector('#system-status').textContent = active ? 'Activo' : 'Pausa de risco';
  document.querySelector('#system-status').className = `status ${active ? 'active' : ''}`;
  document.querySelector('#risk-pause').textContent = active ? 'Dentro do limite' : 'Pausa activa';
  document.querySelector('#next-review').textContent = 'Revisão diária';

  document.querySelector('#decision-list').innerHTML = assetIds.map(asset => {
    const analysis = snapshot.analysis[asset], symbol = config.assets[asset].symbol;
    const posture = analysis.bullish && active ? 'Exposição autorizada' : 'Manter em caixa';
    const reason = analysis.bullish ? `Preço acima das médias de 20 e 60 dias; momentum de ${(analysis.momentum_20d * 100).toFixed(2)}% em 20 dias.` : 'Tendência ainda não confirma exposição.';
    return `<div class="decision-row"><strong>${symbol}</strong><span class="signal ${analysis.bullish && active ? '' : 'neutral'}">${posture}</span><p>${reason}</p></div>`;
  }).join('');

  document.querySelector('#positions').innerHTML = assetIds.map(asset => {
    const symbol = config.assets[asset].symbol, quantity = state.holdings[asset], price = prices[asset].eur, value = quantity * price;
    return `<article class="position"><div class="symbol"><span class="coin-icon">${symbol.slice(0,1)}</span><span>${config.assets[asset].name.toUpperCase()}</span></div><h3>${money.format(value)}</h3><span class="quantity">${quantity.toFixed(6)} ${symbol}</span><div class="position-data"><span>PREÇO LIVE<b>${money.format(price)}</b></span><span>EXPOSIÇÃO<b>${(value / portfolio * 100).toFixed(1)}%</b></span><span>SINAL<b>${snapshot.analysis[asset].bullish ? 'POSITIVO' : 'NEUTRO'}</b></span></div></article>`;
  }).join('');
  renderLedger(entries);
}

Promise.all([fetch('data/dashboard.json', {cache:'no-store'}).then(r => r.json()), readLedger(), currentPrices()])
  .then(([state, entries, prices]) => { dashboard = state; render(prices, entries); setInterval(() => currentPrices().then(next => render(next, entries)).catch(() => {}), 300000); })
  .catch(error => { document.querySelector('#updated').textContent = 'Dados indisponíveis'; console.error(error); });
