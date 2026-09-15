const CACHE_NAME = "soulbound-astro-v1";
const STATIC_URLS = [
    "/",
    "/index.html",
    "/style.css",
    "/app.js",
    "/manifest.json",
    "/health"
];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_URLS)).catch(() => {})
    );
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener("fetch", (event) => {
    const req = event.request;

    if (req.method !== "GET") return;

    const url = new URL(req.url);

    if (url.origin !== self.location.origin) return;

    if (url.pathname.startsWith("/generate") || url.pathname.startsWith("/forecast") || url.pathname.startsWith("/app-token")) {
        event.respondWith(
            fetch(req).catch(() => {
                return new Response(
                    JSON.stringify({ status: "error", message: "Çevrimdışı - lütfen internet bağlantını kontrol et." }),
                    { headers: { "Content-Type": "application/json" } }
                );
            })
        );
        return;
    }

    event.respondWith(
        caches.match(req).then((cached) => {
            const fetchPromise = fetch(req)
                .then((res) => {
                    const clone = res.clone();
                    if (res.ok && (req.mode === "navigate" || url.pathname.match(/\.(css|js|json|png|jpg|svg|ico)$/))) {
                        caches.open(CACHE_NAME).then((cache) => cache.put(req, clone)).catch(() => {});
                    }
                    return res;
                })
                .catch(() => cached);
            return cached || fetchPromise;
        })
    );
});
