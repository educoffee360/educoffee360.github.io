(function () {
  const TAGS = [
    { kind: "link", rel: "stylesheet", href: "/fonts.css" },
    { kind: "link", rel: "manifest", href: "/manifest.json" },
    { kind: "meta", name: "theme-color", content: "#3E2723" },
    { kind: "meta", name: "apple-mobile-web-app-capable", content: "yes" },
    { kind: "meta", name: "apple-mobile-web-app-status-bar-style", content: "default" },
    { kind: "meta", name: "apple-mobile-web-app-title", content: "EduCoffee" },
    { kind: "link", rel: "apple-touch-icon", href: "/assets/icons/icon-192.png" },
    { kind: "link", rel: "icon", href: "/assets/icons/favicon.ico", type: "image/x-icon" },
    { kind: "link", rel: "icon", href: "/assets/icons/favicon-32x32.png", type: "image/png" },
    { kind: "link", rel: "apple-touch-icon", href: "/assets/icons/apple-touch-icon.png" }
  ];

  function hasLink(rel, href) {
    return !!document.head.querySelector(`link[rel="${rel}"][href="${href}"]`);
  }

  function hasMeta(name) {
    return !!document.head.querySelector(`meta[name="${name}"]`);
  }

  function ensure() {
    for (const tag of TAGS) {
      if (tag.kind === "link") {
        if (hasLink(tag.rel, tag.href)) continue;
        const el = document.createElement("link");
        el.rel = tag.rel;
        el.href = tag.href;
        if (tag.type) el.type = tag.type;
        document.head.appendChild(el);
      } else {
        if (hasMeta(tag.name)) continue;
        const el = document.createElement("meta");
        el.name = tag.name;
        el.content = tag.content;
        document.head.appendChild(el);
      }
    }

    if (!document.getElementById("educoffee-pwa-installer")) {
      const script = document.createElement("script");
      script.id = "educoffee-pwa-installer";
      script.src = "/pwa_installer.js";
      script.defer = true;
      document.head.appendChild(script);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", ensure, { once: true });
  } else {
    ensure();
  }
})();
