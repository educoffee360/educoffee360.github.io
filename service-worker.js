const CACHE_NAME = 'educoffee-cache-v4';
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
      return Promise.allSettled(STATIC_ASSETS.map((asset) => cache.add(asset)));
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


// Push notification event
self.addEventListener('push', (event) => {
  let data = {};

  try {
    data = event.data ? event.data.json() : {};
  } catch {
    data = {
      title: 'EduCoffee',
      body: event.data ? event.data.text() : 'You have a new notification.'
    };
  }

  const title = data.title || 'EduCoffee';

  const options = {
    body: data.body || 'You have a new notification.',
    icon: '/assets/icons/icon-192.png',
    badge: '/assets/icons/icon-192.png',
    tag: data.tag || 'educoffee-notification',
    renotify: true,
    data: {
      url: data.url || '/student-notices.html'
    }
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

// Open/focus EduCoffee when a notification is tapped
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  const targetUrl = new URL(
    event.notification.data?.url || '/student-notices.html',
    self.location.origin
  ).href;

  event.waitUntil(
    self.clients.matchAll({
      type: 'window',
      includeUncontrolled: true
    }).then((clientList) => {
      for (const client of clientList) {
        if (client.url.startsWith(self.location.origin) && 'focus' in client) {
          client.navigate(targetUrl);
          return client.focus();
        }
      }

      if (self.clients.openWindow) {
        return self.clients.openWindow(targetUrl);
      }
    })
  );
});

self.addEventListener('fetch', (event) => {
  // Only intercept GET requests
  if (event.request.method !== 'GET') return;

  // API requests must always go directly to the network.
  // Do not intercept or fabricate 503 responses.
  if (event.request.url.includes('/api') || event.request.url.includes('onrender.com')) {
    return;
  }

  // Handle static page / assets caching strategy
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response.status === 200 && response.type === 'basic') {
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        return response;
      })
      .catch(() => {
        return caches.match(event.request).then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }

          if ((event.request.headers.get('accept') || '').includes('text/html')) {
            return caches.match(OFFLINE_URL);
          }

          return new Response('Resource unavailable while offline.', {
            status: 503
          });
        });
      })
  );
});