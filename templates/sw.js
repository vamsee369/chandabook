/* ============================================================
   Chanda Book – Service Worker
   Strategy:
     • Static assets  → Cache-first (long-lived)
     • App pages      → Network-first, fallback to cache
     • Offline page   → shown when network + cache both miss
   ============================================================ */

const CACHE_NAME    = 'chandabook-v1';
const STATIC_CACHE  = 'chandabook-static-v1';
const DYNAMIC_CACHE = 'chandabook-dynamic-v1';

const STATIC_ASSETS = [
  '/',
  '/festivals/',
  '/accounts/login/',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  'https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/dist/tabler-icons.min.css',
];

const OFFLINE_URL = '/offline/';

/* ── Install: pre-cache static assets ── */
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(cache => {
      console.log('[SW] Pre-caching static assets');
      return cache.addAll(STATIC_ASSETS).catch(err => {
        console.warn('[SW] Some assets failed to cache:', err);
      });
    })
  );
  self.skipWaiting();
});

/* ── Activate: clean up old caches ── */
self.addEventListener('activate', event => {
  const KEEP = [STATIC_CACHE, DYNAMIC_CACHE];
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => !KEEP.includes(k)).map(k => {
          console.log('[SW] Deleting old cache:', k);
          return caches.delete(k);
        })
      )
    )
  );
  self.clients.claim();
});

/* ── Fetch: routing strategy ── */
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET and cross-origin (except CDN icons)
  if (request.method !== 'GET') return;
  if (url.origin !== location.origin &&
      !url.hostname.includes('jsdelivr.net') &&
      !url.hostname.includes('cdnjs.cloudflare.com')) return;

  // Static assets → Cache-first
  if (
    url.pathname.startsWith('/static/') ||
    url.hostname.includes('jsdelivr.net') ||
    url.hostname.includes('cdnjs.cloudflare.com')
  ) {
    event.respondWith(cacheFirst(request));
    return;
  }

  // App pages → Network-first, cache fallback
  event.respondWith(networkFirst(request));
});

/* ── Cache-first strategy ── */
async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response('Offline – static asset unavailable', { status: 503 });
  }
}

/* ── Network-first strategy ── */
async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok || response.type === 'opaque') {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    // Show offline page for navigation requests
    if (request.destination === 'document') {
      return caches.match('/offline/') ||
             new Response(offlineFallbackHTML(), {
               status: 503,
               headers: { 'Content-Type': 'text/html; charset=utf-8' }
             });
    }
    return new Response('Offline', { status: 503 });
  }
}

/* ── Inline offline fallback HTML ── */
function offlineFallbackHTML() {
  return `<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Offline – Chanda Book</title>
<style>
  body{font-family:'Segoe UI',sans-serif;background:#f5f0e8;color:#1c1917;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px;}
  .card{background:#fff;border:1.5px solid #e8dfc8;border-radius:18px;padding:36px 28px;max-width:360px;width:100%;text-align:center;box-shadow:0 4px 24px rgba(0,0,0,.08);}
  .icon{font-size:3.5rem;margin-bottom:14px;}
  h1{font-size:1.4rem;font-weight:800;margin-bottom:10px;}
  p{color:#78716c;font-size:.9rem;line-height:1.6;margin-bottom:20px;}
  button{background:#d97706;color:#fff;border:none;border-radius:10px;padding:12px 24px;font-size:.9rem;font-weight:700;cursor:pointer;}
  button:hover{filter:brightness(1.1);}
</style></head><body>
<div class="card">
  <div class="icon">🪔</div>
  <h1>You're Offline</h1>
  <p>No internet connection right now. Previously visited pages may still be available from cache.</p>
  <button onclick="location.reload()">🔄 Try Again</button>
</div>
</body></html>`;
}

/* ── Background sync for queued form submissions ── */
self.addEventListener('sync', event => {
  if (event.tag === 'sync-collections') {
    console.log('[SW] Background sync: collections');
  }
});

/* ── Push notifications (future use) ── */
self.addEventListener('push', event => {
  if (!event.data) return;
  const data = event.data.json();
  self.registration.showNotification(data.title || 'Chanda Book', {
    body: data.body || '',
    icon: '/static/icons/icon-192.png',
    badge: '/static/icons/icon-96.png',
    tag: 'chandabook-notification',
  });
});
