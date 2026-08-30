const money = new Intl.NumberFormat('pt-PT', { style: 'currency', currency: 'EUR' });
const assetIds = ['bitcoin', 'ethereum'];
let dashboard;
let dashboards;
let activeStrategy = 'trend';
let marketPrices;
let chartRange = 'all';
let chartEntries = [];
let chartCurrentValue = 0;
const REFRESH_INTERVAL_MS = 180000;

const signedMoney = value => `${value >= 0 ? '+' : '−'}${money.format(Math.abs(value))}`;
const signedPct = value => `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
const tone = value => value >= 0 ? 'positive' : 'negative';

function currentPrices() {
  return fetch('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=eur', { cache: 'no-store' })
    .then(response => response.ok ? response.json() : Promise.reject(new Error('Mercado indisponível')));
}

function readLedger() {
  return fetch('logs/ledger.jsonl', { cache: 'no-store' })
    .then(response => response.ok ? response.text() : '')
    .then(text => text.trim().split('\n').filter(Boolean).map(line => JSON.parse(line)));
}

// FIFO: every buy carries its execution fee; sells consume the oldest open lots.
function ledgerStats(entries, prices) {
  const lots = Object.fromEntries(assetIds.map(asset => [asset, []]));
  let realized = 0, fees = 0, buys = 0, sells = 0;
  entries.forEach(entry => entry.operations.forEach(op => {
    const fee = Number(op.fee_eur || 0);
    fees += fee;
    if (op.side === 'BUY') {
      buys += 1;
      lots[op.asset].push({ quantity: op.quantity, cost: Number(op.eur) + fee });
      return;
    }
    sells += 1;
    let remaining = op.quantity, costBasis = 0;
    while (remaining > 1e-10 && lots[op.asset]?.length) {
      const lot = lots[op.asset][0];
      const take = Math.min(remaining, lot.quantity);
      costBasis += lot.cost * (take / lot.quantity);
      lot.cost -= lot.cost * (take / lot.quantity);
      lot.quantity -= take;
      remaining -= take;
      if (lot.quantity < 1e-10) lots[op.asset].shift();
    }
    realized += (Number(op.eur) - fee) - costBasis;
  }));
  const byAsset = Object.fromEntries(assetIds.map(asset => {
    const cost = lots[asset].reduce((sum, lot) => sum + lot.cost, 0);
    const quantity = lots[asset].reduce((sum, lot) => sum + lot.quantity, 0);
    const value = quantity * prices[asset].eur;
    return [asset, { cost, quantity, value, pnl: value - cost }];
  }));
  const unrealized = Object.values(byAsset).reduce((sum, item) => sum + item.pnl, 0);
  return { realized, unrealized, fees, buys, sells, byAsset };
}

function chartHistory(entries, currentValue) {
  const key = `opus-capital-history-${activeStrategy}`;
  let local = [];
  try { local = JSON.parse(localStorage.getItem(key) || '[]'); } catch (_) { local = []; }
  const now = Date.now();
  if (!local.length || now - local[local.length - 1].timestamp > 60000) {
    local.push({ timestamp: now, value: currentValue });
    local = local.slice(-180);
    localStorage.setItem(key, JSON.stringify(local));
  }
  return [...entries.map(entry => ({ timestamp: Date.parse(entry.timestamp), value: entry.portfolio_value_eur })), ...local]
    .sort((a, b) => a.timestamp - b.timestamp);
}

function chartDate(timestamp) {
  return new Date(timestamp).toLocaleString('pt-PT', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }).replace(',', '');
}

function chartWindow(history) {
  if (chartRange === 'all') return history;
  const cutoff = Date.now() - (chartRange === 'day' ? 24 : 30 * 24) * 60 * 60 * 1000;
  const visible = history.filter(point => point.timestamp >= cutoff);
  return visible.length ? visible : history.slice(-1);
}

function drawChart(entries, currentValue) {
  chartEntries = entries;
  chartCurrentValue = currentValue;
  const history = chartWindow(chartHistory(entries, currentValue));
  const values = history.length ? history.map(point => point.value) : [currentValue];
  if (values.length === 1) values.push(values[0]);
  const rawMin = Math.min(...values), rawMax = Math.max(...values);
  const padding = Math.max((rawMax - rawMin) * 0.18, 0.015);
  const min = rawMin - padding, max = rawMax + padding, range = max - min;
  const firstTimestamp = history[0]?.timestamp || Date.now();
  const lastTimestamp = history[history.length - 1]?.timestamp || firstTimestamp;
  const duration = Math.max(lastTimestamp - firstTimestamp, 1);
  const points = history.map((point, index) => {
    const x = history.length === 1 ? 0 : ((point.timestamp - firstTimestamp) / duration) * 700;
    return `${x},${156 - ((point.value - min) / range) * 112}`;
  }).join(' ');
  document.querySelector('#chart-line').setAttribute('d', `M ${points.replace(' ', ' L ')}`);
  document.querySelector('#chart-fill').setAttribute('d', `M 0,156 L ${points.replace(' ', ' L ')} L 700,156 Z`);
  document.querySelector('#chart-y-max').textContent = money.format(max);
  document.querySelector('#chart-y-mid').textContent = money.format((max + min) / 2);
  document.querySelector('#chart-y-min').textContent = money.format(min);
  document.querySelector('#chart-x-start').textContent = chartDate(firstTimestamp);
  document.querySelector('#chart-x-middle').textContent = chartDate(firstTimestamp + duration / 2);
  document.querySelector('#chart-x-end').textContent = chartDate(lastTimestamp);
  const windowLabel = { day: ['ÚLTIMAS 24H', 'dados disponíveis'], month: ['ÚLTIMOS 30 DIAS', 'dados disponíveis'], all: ['HISTÓRICO', 'desde o início'] }[chartRange];
  document.querySelector('#chart-window').innerHTML = `${windowLabel[0]}<br /><b>${windowLabel[1]}</b>`;
}

document.querySelectorAll('[data-chart-range]').forEach(button => {
  button.addEventListener('click', () => {
    chartRange = button.dataset.chartRange;
    document.querySelectorAll('[data-chart-range]').forEach(item => item.classList.toggle('active', item === button));
    if (chartEntries.length) drawChart(chartEntries, chartCurrentValue);
  });
});

function renderLedger(entries, portfolio) {
  const operations = entries.flatMap(entry => entry.operations.map(op => ({ ...op, timestamp: entry.timestamp })));
  document.querySelector('#ledger').innerHTML = operations.length ? operations.slice().reverse().map(op => {
    const fee = money.format(op.fee_eur || 0);
    return `<div class="ledger-row"><time>${new Date(op.timestamp).toLocaleString('pt-PT', {dateStyle:'medium', timeStyle:'short'})}</time><span>${op.side === 'BUY' ? 'COMPRA' : 'VENDA'} ${dashboard.config.assets[op.asset].symbol} · ${money.format(op.eur)} · custo ${fee}</span><b class="${op.side === 'BUY' ? 'neutral' : ''}">${op.quantity.toFixed(6)} ${dashboard.config.assets[op.asset].symbol}</b></div>`;
  }).join('') : '<div class="ledger-row"><span>Sem operações.</span></div>';
  drawChart(entries, portfolio);
}

function setMetric(id, value, className = '') {
  const el = document.querySelector(id);
  el.textContent = value;
  el.className = className;
}

function renderSocialSimulation(simulation) {
  document.querySelector('#social-status').textContent = simulation.status;
  document.querySelector('#social-scope').textContent = simulation.scope.join(' · ');
  document.querySelector('#social-stage').textContent = simulation.stage;
  document.querySelector('#social-run').textContent = simulation.last_run_at ? new Date(simulation.last_run_at).toLocaleString('pt-PT', {dateStyle:'medium', timeStyle:'short'}) : 'Ainda não executada';
  document.querySelector('#social-summary').textContent = simulation.summary;
  document.querySelector('#social-guardrails').textContent = simulation.guardrails.join(' · ');
}

function render(prices, entries) {
  const { config, state, snapshot } = dashboard;
  const stats = ledgerStats(entries, prices);
  const holdingsValue = assetIds.reduce((sum, asset) => sum + state.holdings[asset] * prices[asset].eur, 0);
  const portfolio = state.cash_eur + holdingsValue;
  const totalPnl = portfolio - config.starting_capital_eur;
  const totalPnlPct = totalPnl / config.starting_capital_eur * 100;
  const active = !snapshot.risk_pause;
  const realizedGain = Math.max(stats.realized, 0), realizedLoss = Math.min(stats.realized, 0);

  setMetric('#portfolio-value', money.format(portfolio));
  setMetric('#portfolio-return', `${signedMoney(totalPnl)} · ${signedPct(totalPnlPct)}`, tone(totalPnl));
  setMetric('#total-pnl', signedMoney(totalPnl), tone(totalPnl));
  setMetric('#total-pnl-pct', `${signedPct(totalPnlPct)} sobre €200,00`, tone(totalPnl));
  setMetric('#realized-gain', money.format(realizedGain), realizedGain ? 'positive' : 'neutral');
  setMetric('#realized-loss', `perdas realizadas ${money.format(realizedLoss)}`, realizedLoss < 0 ? 'negative' : 'neutral');
  setMetric('#unrealized-pnl', signedMoney(stats.unrealized), tone(stats.unrealized));
  setMetric('#unrealized-pct', `${signedPct((stats.unrealized / config.starting_capital_eur) * 100)} em posições abertas`, tone(stats.unrealized));
  setMetric('#fees-total', money.format(stats.fees), 'negative');
  setMetric('#operations-count', `${stats.buys} compras · ${stats.sells} vendas`);
  setMetric('#cash-value', money.format(state.cash_eur));
  setMetric('#drawdown', `${(state.max_drawdown * 100).toFixed(2)}%`);
  setMetric('#chart-current', money.format(portfolio));
  document.querySelector('#updated').textContent = `PREÇOS · ${new Date().toLocaleTimeString('pt-PT',{hour:'2-digit',minute:'2-digit'})}`;
  document.querySelector('#system-status').textContent = active ? 'Activo' : 'Pausa';
  document.querySelector('#system-status').className = `status ${active ? 'active' : ''}`;
  document.querySelector('#risk-pause').textContent = active ? 'Dentro do limite' : 'Pausa activa';
  document.querySelector('#next-review').textContent = '3 min';

  document.querySelector('#decision-list').innerHTML = assetIds.map(asset => {
    const item = stats.byAsset[asset], symbol = config.assets[asset].symbol;
    return `<div class="decision-row"><strong>${symbol}</strong><span class="signal ${tone(item.pnl)}">${signedMoney(item.pnl)}</span><p>${money.format(item.value)} em posição · custo ${money.format(item.cost)}</p></div>`;
  }).join('');

  document.querySelector('#positions').innerHTML = assetIds.map(asset => {
    const symbol = config.assets[asset].symbol, item = stats.byAsset[asset], price = prices[asset].eur;
    const pnlPct = item.cost ? item.pnl / item.cost * 100 : 0;
    return `<article class="position"><div class="symbol"><span class="coin-icon">${symbol.slice(0,1)}</span><span>${config.assets[asset].name.toUpperCase()}</span></div><h3>${money.format(item.value)}</h3><span class="quantity">${item.quantity.toFixed(6)} ${symbol}</span><div class="position-data"><span>CUSTO<b>${money.format(item.cost)}</b></span><span>PREÇO LIVE<b>${money.format(price)}</b></span><span>P&amp;L<b class="${tone(item.pnl)}">${signedMoney(item.pnl)} · ${signedPct(pnlPct)}</b></span></div></article>`;
  }).join('');
  renderLedger(entries, portfolio);
}

function startRefreshCountdown() {
  const target = Date.now() + REFRESH_INTERVAL_MS;
  const label = document.querySelector('#refresh-countdown');
  const tick = () => {
    const remaining = Math.max(0, target - Date.now());
    const minutes = Math.floor(remaining / 60000).toString().padStart(2, '0');
    const seconds = Math.floor((remaining % 60000) / 1000).toString().padStart(2, '0');
    label.textContent = `REFRESH · ${minutes}:${seconds}`;
    if (remaining <= 0) location.reload();
  };
  tick();
  setInterval(tick, 1000);
}

Promise.all([
  fetch('data/dashboard.json', {cache:'no-store'}).then(r => r.json()), readLedger(), currentPrices(),
  fetch('data/social-simulation.json', {cache:'no-store'}).then(r => r.json())
])
  .then(([trend, trendEntries, prices, socialSimulation]) => {
    dashboards = {trend, 'trend-entries': trendEntries};
    marketPrices = prices;
    dashboard = trend;
    render(prices, trendEntries);
    renderSocialSimulation(socialSimulation);
    startRefreshCountdown();
  })
  .catch(error => { document.querySelector('#updated').textContent = 'Dados indisponíveis'; console.error(error); });
