/* Fabrything service worker.
 *
 * Its ONLY jobs are (a) to make the site installable — Chrome refuses the
 * install prompt without a fetch handler — and (b) to make repeat launches of
 * the installed app fast. It is deliberately NOT an offline cache.
 *
 * THE RULE THIS FILE EXISTS TO ENFORCE: never serve stale HTML, and never
 * serve a cached API response.
 *
 * A misbehaving service worker is the single worst thing that can happen to a
 * shop — it pins customers to an old bundle or an old price for days, and no
 * amount of hard-refreshing on their side fixes it. So:
 *
 *   - navigations (HTML)  -> NETWORK ONLY, with a cached shell used *only*
 *                            when the network genuinely fails. A deploy is
 *                            therefore visible on the very next load.
 *   - /api/ requests      -> not intercepted at all. Prices, stock, banners
 *                            and orders always come from the server.
 *   - hashed build assets -> cache first. Safe by construction: CRA puts a
 *                            content hash in every filename, so a changed file
 *                            is a different URL and can never be stale.
 *   - images              -> stale-while-revalidate, capped, because product
 *                            photos are the bulk of the bytes on rural data.
 *
 * Bump CACHE_VERSION to evict everything on the next activation.
 */
const CACHE_VERSION = 'v1';
const STATIC_CACHE = `fabrything-static-${CACHE_VERSION}`;
const IMAGE_CACHE = `fabrything-img-${CACHE_VERSION}`;
const OFFLINE_SHELL = '/index.html';
const MAX_IMAGES = 120;

self.addEventListener('install', (event) => {
  // Only the shell, and only as an offline last resort — see the fetch
  // handler, which always tries the network for navigations first.
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => cache.addAll([OFFLINE_SHELL])).catch(() => {}),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((k) => k.startsWith('fabrything-') && !k.endsWith(CACHE_VERSION))
            .map((k) => caches.delete(k)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

// The page asks for this after the user accepts the "new version" prompt.
self.addEventListener('message', (event) => {
  if (event.data === 'SKIP_WAITING') self.skipWaiting();
});

function isHashedAsset(url) {
  // CRA emits /static/js/main.<hash>.js, /static/css/*.<hash>.css, and media
  // with a hash too. The hash is what makes cache-first safe here.
  return url.pathname.startsWith('/static/');
}

function isImage(request, url) {
  return (
    request.destination === 'image' ||
    /\.(png|jpe?g|webp|avif|gif|svg)$/i.test(url.pathname) ||
    url.pathname.startsWith('/api/media/')   // content-addressed: immutable
  );
}

async function trimCache(name, max) {
  const cache = await caches.open(name);
  const keys = await cache.keys();
  if (keys.length <= max) return;
  await Promise.all(keys.slice(0, keys.length - max).map((k) => cache.delete(k)));
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  let url;
  try {
    url = new URL(request.url);
  } catch {
    return;
  }

  // Anything on another origin (the API host, fonts, partner images) is left
  // entirely alone — intercepting cross-origin requests risks breaking CORS
  // and gains nothing.
  if (url.origin !== self.location.origin) return;

  // API traffic is never cached, never intercepted. This is the line that
  // guarantees a price, a stock level or a banner is always live.
  if (url.pathname.startsWith('/api/')) return;

  // HTML: network first, always. The cached shell is a fallback for a genuine
  // network failure only, so a new deploy is picked up on the next load.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(STATIC_CACHE).then((c) => c.put(OFFLINE_SHELL, copy)).catch(() => {});
          return response;
        })
        .catch(() => caches.match(OFFLINE_SHELL).then((r) => r || Response.error())),
    );
    return;
  }

  if (isHashedAsset(url)) {
    event.respondWith(
      caches.match(request).then(
        (hit) =>
          hit ||
          fetch(request).then((response) => {
            if (response.ok) {
              const copy = response.clone();
              caches.open(STATIC_CACHE).then((c) => c.put(request, copy)).catch(() => {});
            }
            return response;
          }),
      ),
    );
    return;
  }

  if (isImage(request, url)) {
    event.respondWith(
      caches.open(IMAGE_CACHE).then(async (cache) => {
        const hit = await cache.match(request);
        const network = fetch(request)
          .then((response) => {
            if (response.ok) {
              cache.put(request, response.clone()).then(() => trimCache(IMAGE_CACHE, MAX_IMAGES));
            }
            return response;
          })
          .catch(() => hit);
        return hit || network;
      }),
    );
  }
});
