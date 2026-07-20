const VERSION = 'choin-v2';
const PRECACHE = [
  './',
  './index.html',
  './support.js',
  './manifest.webmanifest',
  './icon-192.png',
  './icon-512.png',
  './icon-512-maskable.png',
  './icon-180.png',
  'https://unpkg.com/react@18.3.1/umd/react.production.min.js',
  'https://unpkg.com/react-dom@18.3.1/umd/react-dom.production.min.js'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(VERSION)
      .then(c => Promise.allSettled(PRECACHE.map(u => c.add(u))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request).then(res => {
        if (res && res.ok) {
          const copy = res.clone();
          caches.open(VERSION).then(c => c.put('./index.html', copy));
        }
        return res;
      }).catch(() => caches.match('./index.html'))
    );
    return;
  }
  e.respondWith(
    caches.match(e.request, { ignoreSearch: true }).then(hit => {
      const net = fetch(e.request).then(res => {
        if (res && res.ok) {
          const copy = res.clone();
          caches.open(VERSION).then(c => c.put(e.request, copy));
        }
        return res;
      }).catch(() => hit);
      return hit || net;
    })
  );
});

function idbOpen() {
  return new Promise((res, rej) => {
    const req = indexedDB.open('choin-sw', 1);
    req.onupgradeneeded = () => { req.result.createObjectStore('kv'); };
    req.onsuccess = () => res(req.result);
    req.onerror = () => rej(req.error);
  });
}
function idbGet(key) {
  return idbOpen().then(db => new Promise(res => {
    const g = db.transaction('kv', 'readonly').objectStore('kv').get(key);
    g.onsuccess = () => res(g.result);
    g.onerror = () => res(null);
  })).catch(() => null);
}
function idbPut(key, val) {
  return idbOpen().then(db => new Promise(res => {
    const tx = db.transaction('kv', 'readwrite');
    tx.objectStore('kv').put(val, key);
    tx.oncomplete = () => res();
    tx.onerror = () => res();
  })).catch(() => {});
}

self.addEventListener('periodicsync', e => {
  if (e.tag !== 'choin-remind') return;
  e.waitUntil((async () => {
    const cfg = await idbGet('cfg');
    if (!cfg || !cfg.notif) return;
    const now = new Date();
    const h = now.getHours(), day = now.getDay();
    const r = cfg.risk || [];
    let w = null;
    if (r.includes('심야') && (h >= 22 || h < 2)) w = '심야';
    else if (r.includes('아침') && h >= 6 && h < 9) w = '아침';
    else if (r.includes('주말') && (day === 0 || day === 6) && h >= 20) w = '주말';
    if (!w) return;
    const k = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0') + '-' + String(now.getDate()).padStart(2, '0') + ':' + w;
    if (cfg.lastNotifDay === k) return;
    cfg.lastNotifDay = k;
    await idbPut('cfg', cfg);
    await self.registration.showNotification('초인타임', {
      body: cfg.notifText || '수련 시간이다',
      icon: './icon-192.png',
      badge: './icon-192.png',
      tag: 'choin-risk'
    });
  })());
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      for (const c of list) { if ('focus' in c) return c.focus(); }
      return clients.openWindow('./');
    })
  );
});
