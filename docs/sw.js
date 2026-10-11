const CACHE_NAME = 'radar-v28';
const SHELL_URLS = [
  './',
  './index.html',
  './manifest.json',
  './icon-192.png',
  './icon-512.png'
];

// Instala: cacheia o que conseguir (não bloqueia se ícone falhar)
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      return Promise.allSettled(
        SHELL_URLS.map(function(url) {
          return cache.add(url).catch(function() {});
        })
      );
    }).then(function() {
      return self.skipWaiting();
    })
  );
});

// Responde a SKIP_WAITING da página
self.addEventListener('message', function(event) {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// Ativa: limpa caches antigos
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(names) {
      return Promise.all(
        names.filter(function(n) { return n !== CACHE_NAME && n !== NOTIFY_LOG_CACHE; })
             .map(function(n) { return caches.delete(n); })
      );
    }).then(function() {
      return self.clients.claim();
    })
  );
});

// Fetch: network-first, fallback to cache
self.addEventListener('fetch', function(event) {
  if (event.request.method !== 'GET') return;

  event.respondWith(
    fetch(event.request).then(function(response) {
      if (response.ok) {
        var clone = response.clone();
        caches.open(CACHE_NAME).then(function(cache) {
          cache.put(event.request, clone);
        });
      }
      return response;
    }).catch(function() {
      return caches.match(event.request);
    })
  );
});

// ===== BACKGROUND PRICE CHECK =====
// Periodic Background Sync: Chrome Android acorda o SW periodicamente
// pra checar preços mesmo com o app fechado.
// Limitação: o navegador decide quando acordar (pode ser 1x por hora ou menos).

self.addEventListener('periodicsync', function(event) {
  if (event.tag === 'check-prices') {
    event.waitUntil(checkPricesInBackground());
  }
});

// Estratégia de tendência (a mesma de radar.html → TREND), em candles diários:
// entra ao fechar acima da máxima de 20 dias com média de 20 > média de 50;
// sai ao fechar abaixo da mínima de 10 dias. Só avisa eventos do último candle fechado.
var TREND = { breakout: 20, exit: 10, fast: 20, slow: 50 };
var BG_PAIRS = {
  bitcoin: ['BTC', 'BTCUSDT'], ethereum: ['ETH', 'ETHUSDT'], solana: ['SOL', 'SOLUSDT'], ripple: ['XRP', 'XRPUSDT'],
  dogecoin: ['DOGE', 'DOGEUSDT'], 'avalanche-2': ['AVAX', 'AVAXUSDT'], sui: ['SUI', 'SUIUSDT'], pepe: ['PEPE', 'PEPEUSDT'],
  binancecoin: ['BNB', 'BNBUSDT'], cardano: ['ADA', 'ADAUSDT'], chainlink: ['LINK', 'LINKUSDT']
};

function emaSeries(values, n) {
  var k = 2 / (n + 1), out = [], e = null;
  for (var i = 0; i < values.length; i++) {
    if (i < n - 1) { out.push(null); continue; }
    if (e === null) { e = 0; for (var j = i - n + 1; j <= i; j++) e += values[j]; e /= n; }
    else e = values[i] * k + e * (1 - k);
    out.push(e);
  }
  return out;
}

// Retorna o evento do último candle fechado: 'buy', 'sell' ou null
function lastTrendEvent(c) {
  var ef = emaSeries(c, TREND.fast), es = emaSeries(c, TREND.slow), inPos = false, ev = null;
  for (var i = TREND.slow; i < c.length; i++) {
    ev = null;
    if (inPos && c[i] < Math.min.apply(null, c.slice(i - TREND.exit, i))) { inPos = false; ev = 'sell'; }
    else if (!inPos && ef[i] > es[i] && c[i] > Math.max.apply(null, c.slice(i - TREND.breakout, i))) { inPos = true; ev = 'buy'; }
  }
  return ev;
}

// Mesmas regras anti-spam da página (radar.html → claimNotification), no mesmo registro:
// até 6 avisos por dia, 30 min entre avisos, silêncio 22h–8h; uma chave já avisada hoje ou ontem não repete.
var NOTIFY_LOG_CACHE = 'radar-notify-log';
var NOTIFY_LOG_URL = './__notify-log';

function brtDayHour(ms) {
  var o = {};
  new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Sao_Paulo', year: 'numeric', month: '2-digit', day: '2-digit', hour: 'numeric', hourCycle: 'h23' })
    .formatToParts(new Date(ms)).forEach(function(p) { o[p.type] = p.value; });
  return { day: o.year + '-' + o.month + '-' + o.day, hour: Number(o.hour) };
}

async function claimNotification(keys) {
  var now = Date.now();
  var t = brtDayHour(now);
  if (t.hour >= 22 || t.hour < 8) return [];
  var log = null;
  try { var r = await (await caches.open(NOTIFY_LOG_CACHE)).match(NOTIFY_LOG_URL); if (r) log = await r.json(); } catch (e) {}
  if (!log || log.day !== t.day) log = { day: t.day, keys: [], times: [], prev: log && log.day === brtDayHour(now - 86400000).day ? log.keys : [] };
  var seen = log.keys.concat(log.prev || []);
  var fresh = keys.filter(function(k) { return seen.indexOf(k) === -1; });
  if (!fresh.length || log.times.length >= 6) return [];
  if (log.times.length && now - log.times[log.times.length - 1] < 30 * 60000) return [];
  log.keys = log.keys.concat(fresh);
  log.times.push(now);
  try { await (await caches.open(NOTIFY_LOG_CACHE)).put(NOTIFY_LOG_URL, new Response(JSON.stringify(log), { headers: { 'Content-Type': 'application/json' } })); } catch (e) {}
  return fresh;
}

async function checkPricesInBackground() {
  try {
    var events = [];
    var ids = Object.keys(BG_PAIRS);
    for (var i = 0; i < ids.length; i++) {
      try {
        var resp = await fetch('https://api.binance.com/api/v3/klines?symbol=' + BG_PAIRS[ids[i]][1] + '&interval=1d&limit=90');
        if (!resp.ok) continue;
        var kl = await resp.json();
        kl = kl.slice(0, -1); // candle de hoje ainda não fechou
        if (kl.length <= TREND.slow) continue;
        var ev = lastTrendEvent(kl.map(function(k) { return parseFloat(k[4]); }));
        var day = new Date(kl[kl.length - 1][0]).toISOString().slice(0, 10);
        if (ev) events.push({ key: 'trend-' + ev + ':' + ids[i] + ':' + day, sym: BG_PAIRS[ids[i]][0], type: ev });
      } catch (e) {}
    }
    if (!events.length) return;
    var fresh = await claimNotification(events.map(function(e) { return e.key; }));
    var list = events.filter(function(e) { return fresh.indexOf(e.key) !== -1; });
    if (!list.length) return;
    var word = function(e) { return e.type === 'buy' ? 'entrar em ' + e.sym : 'sair de ' + e.sym; };
    var title = list.length === 1 ? 'Tendência: ' + word(list[0]) : 'Tendência: ' + list.length + ' sinais novos';
    var body = list.length === 1
      ? (list[0].type === 'buy' ? list[0].sym + ' rompeu a máxima de 20 dias em tendência de alta.' : list[0].sym + ' perdeu a mínima de 10 dias.') + ' Abra o Radar para ver os detalhes.'
      : list.map(word).join(' · ');
    await self.registration.showNotification(title, { body: body, tag: 'radar-tendencia', icon: './icon-192.png', badge: './icon-192.png' });
  } catch (e) {
    // Falha silenciosa: o próximo periodic sync tenta de novo
  }
}

// Notificação: foca na aba do radar ao clicar
self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then(function(clientList) {
      for (var i = 0; i < clientList.length; i++) {
        var client = clientList[i];
        if (client.url && 'focus' in client) return client.focus();
      }
      if (clients.openWindow) return clients.openWindow('./');
    })
  );
});
