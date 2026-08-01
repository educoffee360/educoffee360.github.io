// 1. Register Service Worker on load
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js')
      .then((reg) => {
        console.log('[Service Worker] Registered successfully with scope: ', reg.scope);
      })
      .catch((err) => {
        console.warn('[Service Worker] Registration failed: ', err);
      });
  });
}

// 2. Manage App Installation Flow
let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
  // Prevent Chrome 67 and earlier from automatically showing the prompt
  e.preventDefault();
  // Stash the event so it can be triggered later
  deferredPrompt = e;
  
  // Create and show the custom install banner if not already present
  showInstallBanner();
});

function showInstallBanner() {
  // Do not duplicate banner
  if (document.getElementById('educoffee-pwa-banner')) return;

  // Create PWA install notification styled perfectly with EduCoffee tokens
  const banner = document.createElement('div');
  banner.id = 'educoffee-pwa-banner';
  banner.style.cssText = `
    position: fixed;
    bottom: 24px;
    left: 24px;
    right: 24px;
    max-width: 480px;
    margin: 0 auto;
    background: #FFFFFF;
    border: 1.5px solid rgba(62,39,35,.15);
    border-radius: 20px;
    box-shadow: 0 12px 40px rgba(62,39,35,0.18);
    padding: 16px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    z-index: 9999;
    animation: slideUpPwa 0.5s cubic-bezier(0.16, 1, 0.3, 1) both;
    font-family: 'Sora', 'DM Sans', sans-serif;
  `;

  // Inject keyframes to document head for smooth slide-up
  if (!document.getElementById('pwa-keyframes')) {
    const style = document.createElement('style');
    style.id = 'pwa-keyframes';
    style.innerHTML = `
      @keyframes slideUpPwa {
        from { opacity: 0; transform: translateY(40px) scale(0.95); }
        to { opacity: 1; transform: translateY(0) scale(1); }
      }
      @keyframes slideDownPwa {
        to { opacity: 0; transform: translateY(40px) scale(0.95); }
      }
    `;
    document.head.appendChild(style);
  }

  banner.innerHTML = `
    <div style="display: flex; align-items: center; gap: 12px; min-width: 0;">
      <div style="font-size: 2rem; flex-shrink: 0;">☕</div>
      <div style="min-width: 0;">
        <h4 style="margin: 0; font-family: 'DM Serif Display', serif; font-size: 1.05rem; color: #3E2723; font-weight: 700;">Install EduCoffee</h4>
        <p style="margin: 3px 0 0; font-size: 0.78rem; color: #7D6E64; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">Add to your home screen for quick access.</p>
      </div>
    </div>
    <div style="display: flex; align-items: center; gap: 10px; flex-shrink: 0;">
      <button id="pwa-close-btn" style="background: none; border: none; font-size: 0.82rem; font-weight: 600; color: #7D6E64; cursor: pointer; padding: 6px 10px; border-radius: 8px;">Later</button>
      <button id="pwa-install-btn" style="background: #3E2723; border: none; color: #FFFFFF; font-size: 0.8rem; font-weight: 700; padding: 10px 18px; border-radius: 50px; cursor: pointer; transition: background 0.2s;">Install</button>
    </div>
  `;

  document.body.appendChild(banner);

  // Handle Close Button Click
  document.getElementById('pwa-close-btn').addEventListener('click', () => {
    dismissBanner();
  });

  // Handle Install Button Click
  document.getElementById('pwa-install-btn').addEventListener('click', () => {
    if (!deferredPrompt) return;
    
    // Show native prompt
    deferredPrompt.prompt();
    
    // Wait for the user response
    deferredPrompt.userChoice.then((choiceResult) => {
      if (choiceResult.outcome === 'accepted') {
        console.log('[PWA Installer] User accepted the installation');
      } else {
        console.log('[PWA Installer] User dismissed the installation');
      }
      deferredPrompt = null;
      dismissBanner();
    });
  });
}

function dismissBanner() {
  const banner = document.getElementById('educoffee-pwa-banner');
  if (banner) {
    banner.style.animation = 'slideDownPwa 0.4s cubic-bezier(0.16, 1, 0.3, 1) both';
    setTimeout(() => {
      banner.remove();
    }, 400);
  }
}

// Track when app is installed successfully
window.addEventListener('appinstalled', () => {
  console.log('[PWA Installer] EduCoffee app installed successfully');
  dismissBanner();
});