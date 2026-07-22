const $ = (s) => document.querySelector(s);
const esc = (value = '') => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = (n) => Number(n).toLocaleString('zh-TW', {minimumFractionDigits: 2, maximumFractionDigits: 2});
let report;

function renderMarket(cards = []) {
  $('#market-cards').innerHTML = cards.map(c => {
    const cls = c.change > 0 ? 'up' : c.change < 0 ? 'down' : 'flat';
    return `<article class="market-card"><div class="name">${esc(c.name)}</div><div class="price">${money(c.price)}</div><div class="change ${cls}">${c.change > 0 ? '▲' : c.change < 0 ? '▼' : '—'} ${Math.abs(c.change).toFixed(2)}%</div>${c.tag ? `<span class="tag">${esc(c.tag)}</span>` : ''}</article>`;
  }).join('');
}
function renderStrategy(strategy) {
  $('#strategy-copy').innerHTML = `<h2>${esc(strategy.title)}</h2><p>${esc(strategy.subtitle)}</p>`;
  const list = $('#strategy-list');
  if (!strategy.items?.length) { list.innerHTML = $('#empty').innerHTML; return; }
  list.innerHTML = strategy.items.map((item, index) => `<article class="stock"><span class="rank">${String(index + 1).padStart(2,'0')}</span><div><div class="stock-name">${esc(item.name)}</div><div class="stock-code">${esc(item.code)}</div></div><div><div class="stock-price">${money(item.price)}</div><div class="score">評分 ${Number(item.score).toFixed(1)}</div></div>${item.tag ? `<span class="tag">${esc(item.tag)}</span>` : ''}</article>`).join('');
}
function renderTabs(strategies) {
  const tabs = $('#tabs');
  if (!strategies.length) { $('#strategy-copy').innerHTML = '<h2>策略掃描</h2><p>等待每日盤後資料更新</p>'; $('#strategy-list').innerHTML = $('#empty').innerHTML; return; }
  strategies.forEach((strategy, index) => { const b = document.createElement('button'); b.textContent = strategy.title; b.className = index ? '' : 'active'; b.onclick = () => { [...tabs.children].forEach(x => x.classList.remove('active')); b.classList.add('active'); renderStrategy(strategy); window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('light'); }; tabs.append(b); });
  renderStrategy(strategies[0]);
}
function render(data) {
  report = data; $('#updated').textContent = `資料最後同步：${data.updatedAt}`; $('#report-date').textContent = `(${data.date})`; $('#market-name').textContent = `${data.market}｜收盤後策略掃描`;
  renderMarket(data.marketCards); renderTabs(data.strategies || []);
  $('#macro').innerHTML = (data.macro || []).map(x => `<article class="macro-card"><div class="label">${esc(x.label)}</div><div class="price">${esc(x.value)}</div></article>`).join('');
  $('#news').innerHTML = (data.news?.length ? data.news.map(x => `<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.title)}</a>`).join('') : '<div class="empty">今日暫無關鍵新聞</div>');
  $('#closing').textContent = data.closing || ''; $('#disclaimer').textContent = data.disclaimer || '';
}
async function init() { try { const res = await fetch(`report.json?v=${Date.now()}`, {cache:'no-store'}); if (!res.ok) throw new Error(); render(await res.json()); } catch { $('#updated').textContent = '尚未產生盤後資料，請等待排程完成'; } window.Telegram?.WebApp?.ready(); window.Telegram?.WebApp?.expand(); }
init();
