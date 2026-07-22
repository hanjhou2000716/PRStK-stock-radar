<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <meta name="theme-color" content="#101923"><title>PRStK｜稜量盤後速覽</title>
  <link rel="stylesheet" href="style.css"><script src="https://telegram.org/js/telegram-web-app.js"></script>
</head>
<body>
  <main class="app-shell">
    <header class="hero">
      <div class="brand-images">
        <img src="assets/PRStK-Remove.png" alt="PRStK" class="brand-logo">
        <img src="assets/D.inv-removebg-preview.png" alt="D.inv" class="module-logo">
      </div>
      <div class="live-row"><span class="live-dot"></span><span id="updated">正在取得最新盤後資料</span></div>
    </header>
    <section class="headline"><p class="eyebrow">POST-MARKET INTELLIGENCE</p><h1>稜量盤後速覽 <span id="report-date"></span></h1><p id="market-name">市場資料載入中</p></section>
    <section class="section"><div class="section-heading"><h2>📊 市場收盤概況</h2><span>Close</span></div><div id="market-cards" class="market-grid"></div></section>
    <nav id="tabs" class="tabs" aria-label="策略分類"></nav>
    <section class="section strategy-section"><div id="strategy-copy" class="strategy-copy"></div><div id="strategy-list" class="stock-list"></div></section>
    <section class="section"><div class="section-heading"><h2>🧭 市場溫度</h2><span>Macro</span></div><div id="macro" class="macro-grid"></div></section>
    <section class="section"><div class="section-heading"><h2>📰 關鍵新聞</h2><span>News</span></div><div id="news" class="news-list"></div></section>
    <footer><p id="closing"></p><small id="disclaimer"></small></footer>
  </main>
  <template id="empty"><div class="empty">今日尚無符合此策略的標的</div></template>
  <script src="app.js"></script>
</body></html>
