const CACHE_NAME = 'educoffee-cache-v1';
const OFFLINE_URL = '/offline.html';

// Assets to cache immediately for offline capability
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/auth.html',
  '/offline.html',
  '/api.js',
  'https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=Sora:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600&family=Playfair+Display:ital,wght@0,700;1,700&family=DM+Sans:wght@300;400;500;600&display=swap'
];

// Install Event - Pre-cache critical offline shell
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[Service Worker] Pre-caching offline pages and assets');
      return cache.addAll(STATIC_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

// Activate Event - Clean up older caches automatically
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            console.log('[Service Worker] Clearing old cache storage:', cache);
            return caches.delete(cache);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch Event - Handle offline fallback and performant cache strategy
self.addEventListener('fetch', (event) => {
  // Only intercept GET requests
  if (event.request.method !== 'GET') return;

  // Bypass API requests to handle them with fresh network calls
  if (event.request.url.includes('/api') || event.request.url.includes('onrender.com')) {
    event.respondWith(
      fetch(event.request).catch(() => {
        // If API call fails offline, we can intercept and return a JSON error structure if expected
        if (event.request.headers.get('accept').includes('application/json')) {
          return new Response(JSON.stringify({ detail: "You are currently offline. Check your internet connection." }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' }
          });
        }
      })
    );
    return;
  }

  // Handle static page / assets caching strategy (Network falling back to cache, then offline fallback page)
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // If response is valid, clone and put it into static cache
        if (response.status === 200 && response.type === 'basic') {
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        return response;
      })
      .catch(() => {
        // Network failed, look in cache first
        return caches.match(event.request).then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }
          // If request is an HTML page and not in cache, fallback to offline.html
          if (event.request.headers.get('accept').includes('text/html')) {
            return caches.match(OFFLINE_URL);
          }
        });
      })
  );
});