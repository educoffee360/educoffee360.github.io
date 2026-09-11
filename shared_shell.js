(function () {
  const SHELLS = {
    student: "<aside class=\"sidebar\" id=\"sidebar\">\n<div class=\"sidebar-logo\">Edu<span>Coffee.</span></div>\n<nav class=\"sidebar-nav\">\n<div class=\"nav-section\">Main</div>\n<a class=\"nav-link active\" href=\"student-dashboard.html\">\n<svg fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" viewbox=\"0 0 24 24\"><path d=\"M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z\"></path><polyline points=\"9 22 9 12 15 12 15 22\"></polyline></svg>\n            Dashboard\n        </a>\n<a class=\"nav-link\" href=\"student-notices.html\">\n<svg fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" viewbox=\"0 0 24 24\"><path d=\"M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9\"></path><path d=\"M13.73 21a2 2 0 0 1-3.46 0\"></path></svg>\n            Notices\n        </a>\n<a class=\"nav-link\" href=\"student-results.html\">\n<svg fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" viewbox=\"0 0 24 24\"><path d=\"M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z\"></path><polyline points=\"14 2 14 8 20 8\"></polyline><line x1=\"16\" x2=\"8\" y1=\"13\" y2=\"13\"></line><line x1=\"16\" x2=\"8\" y1=\"17\" y2=\"17\"></line></svg>\n            Results\n        </a>\n<div class=\"nav-section\" style=\"margin-top:10px\">Account</div>\n<a class=\"nav-link\" href=\"student-profile.html\">\n<svg fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" viewbox=\"0 0 24 24\"><circle cx=\"12\" cy=\"8\" r=\"4\"></circle><path d=\"M4 20c0-4 3.6-7 8-7s8 3 8 7\"></path></svg>\n            Profile\n        </a>\n</nav>\n<div class=\"sidebar-footer\">\n<div class=\"user-chip\" onclick=\"location.href='student-profile.html'\">\n<div class=\"user-avatar\" id=\"sidebarAvatar\">S</div>\n<div class=\"user-info\">\n<div class=\"user-name\" id=\"sidebarName\">Student</div>\n<div class=\"user-role\">Student/Parent</div>\n</div>\n<button class=\"logout-btn\" onclick=\"event.stopPropagation();doLogout()\" title=\"Logout\">\n<svg fill=\"none\" height=\"16\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" viewbox=\"0 0 24 24\" width=\"16\"><path d=\"M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4\"></path><polyline points=\"16 17 21 12 16 7\"></polyline><line x1=\"21\" x2=\"9\" y1=\"12\" y2=\"12\"></line></svg>\n</button>\n</div>\n</div>\n</aside>\n<header class=\"mobile-header\">\n<a class=\"mobile-logo\" href=\"student-dashboard.html\">Edu<span>Coffee.</span></a>\n<button class=\"hamburger\" onclick=\"toggleSidebar()\">\n<svg fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-width=\"2.5\" viewbox=\"0 0 24 24\"><line x1=\"3\" x2=\"21\" y1=\"6\" y2=\"6\"></line><line x1=\"3\" x2=\"21\" y1=\"12\" y2=\"12\"></line><line x1=\"3\" x2=\"21\" y1=\"18\" y2=\"18\"></line></svg>\n</button>\n</header>\n<div class=\"mobile-overlay\" id=\"mobileOverlay\" onclick=\"closeSidebar()\"></div>\n<nav class=\"bottom-nav\">\n<div class=\"bnav-inner\">\n<a class=\"bnav-item active\" href=\"student-dashboard.html\">\n<svg fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" viewbox=\"0 0 24 24\"><path d=\"M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z\"></path><polyline points=\"9 22 9 12 15 12 15 22\"></polyline></svg>\n            Home\n        </a>\n<a class=\"bnav-item\" href=\"student-notices.html\">\n<svg fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" viewbox=\"0 0 24 24\"><path d=\"M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9\"></path><path d=\"M13.73 21a2 2 0 0 1-3.46 0\"></path></svg>\n            Notices\n        </a>\n<a class=\"bnav-item\" href=\"student-results.html\">\n<svg fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" viewbox=\"0 0 24 24\"><path d=\"M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z\"></path><polyline points=\"14 2 14 8 20 8\"></polyline><line x1=\"16\" x2=\"8\" y1=\"13\" y2=\"13\"></line><line x1=\"16\" x2=\"8\" y1=\"17\" y2=\"17\"></line></svg>\n            Results\n        </a>\n<a class=\"bnav-item\" href=\"student-profile.html\">\n<svg fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" viewbox=\"0 0 24 24\"><circle cx=\"12\" cy=\"8\" r=\"4\"></circle><path d=\"M4 20c0-4 3.6-7 8-7s8 3 8 7\"></path></svg>\n            Profile\n        </a>\n</div>\n</nav>",
    teacher: "<aside class=\"sidebar\" id=\"sidebar\">\n<a class=\"sl\" href=\"teacher-dashboard.html\">Edu<span>Coffee.</span></a>\n<nav class=\"snav\">\n<div class=\"nsec\">Dashboard</div>\n<a class=\"nl active\" href=\"teacher-dashboard.html\">\n<svg fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" viewbox=\"0 0 24 24\"><path d=\"M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z\"></path><polyline points=\"9 22 9 12 15 12 15 22\"></polyline></svg>\n            Overview\n        </a>\n<div class=\"nsec\">Manage</div>\n<a class=\"nl\" href=\"teacher-batches.html\">\n<svg fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" viewbox=\"0 0 24 24\"><rect height=\"14\" rx=\"2\" width=\"20\" x=\"2\" y=\"7\"></rect><path d=\"M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2\"></path></svg>\n            Batches\n        </a>\n<a class=\"nl\" href=\"teacher-students.html\">\n<svg fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" viewbox=\"0 0 24 24\"><path d=\"M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2\"></path><circle cx=\"9\" cy=\"7\" r=\"4\"></circle><path d=\"M23 21v-2a4 4 0 0 0-3-3.87\"></path><path d=\"M16 3.13a4 4 0 0 1 0 7.75\"></path></svg>\n            Students\n        </a>\n<a class=\"nl\" href=\"teacher-notices.html\">\n<svg fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" viewbox=\"0 0 24 24\"><path d=\"M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9\"></path><path d=\"M13.73 21a2 2 0 0 1-3.46 0\"></path></svg>\n            Notices\n        </a>\n<a class=\"nl\" href=\"attendance.html\">\n<svg fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" viewbox=\"0 0 24 24\"><path d=\"M4 19h16\"></path><path d=\"M7 15l3 3 7-8\"></path></svg>\n            Attendance\n        </a>\n<a class=\"nl\" href=\"teacher-results.html\">\n<svg fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" viewbox=\"0 0 24 24\"><path d=\"M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z\"></path><polyline points=\"14 2 14 8 20 8\"></polyline><line x1=\"16\" x2=\"8\" y1=\"13\" y2=\"13\"></line><line x1=\"16\" x2=\"8\" y1=\"17\" y2=\"17\"></line></svg>\n            Results\n        </a>\n<div class=\"nsec\">Account</div>\n<a class=\"nl\" href=\"teacher-profile.html\">\n<svg fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" viewbox=\"0 0 24 24\"><circle cx=\"12\" cy=\"8\" r=\"4\"></circle><path d=\"M4 20c0-4 3.6-7 8-7s8 3 8 7\"></path></svg>\n            Profile &amp; Settings\n        </a>\n</nav>\n<div class=\"sfooter\">\n<div class=\"uc\" onclick=\"location.href='teacher-profile.html'\">\n<div class=\"uav\">T</div>\n<div style=\"flex:1;min-width:0\">\n<div class=\"un\" id=\"teacherName\">Teacher</div>\n<div class=\"ur\" id=\"teacherEmail\">Teacher Account</div>\n</div>\n<button class=\"lob\" onclick=\"event.stopPropagation();doLogout()\" title=\"Logout\">\n<svg fill=\"none\" height=\"16\" stroke=\"currentColor\" stroke-width=\"2\" viewbox=\"0 0 24 24\" width=\"16\"><path d=\"M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4\"></path><polyline points=\"16 17 21 12 16 7\"></polyline><line x1=\"21\" x2=\"9\" y1=\"12\" y2=\"12\"></line></svg>\n</button>\n</div>\n</div>\n</aside>\n<header class=\"mhdr\">\n<a class=\"mlogo\" href=\"teacher-dashboard.html\">Edu<span>Coffee.</span></a>\n<button class=\"ham\" onclick=\"toggleSB()\">\n<svg fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-width=\"2.5\" viewbox=\"0 0 24 24\"><line x1=\"3\" x2=\"21\" y1=\"6\" y2=\"6\"></line><line x1=\"3\" x2=\"21\" y1=\"12\" y2=\"12\"></line><line x1=\"3\" x2=\"21\" y1=\"18\" y2=\"18\"></line></svg>\n</button>\n</header>\n<div class=\"mov\" id=\"mov\" onclick=\"closeSB()\"></div>\n<a class=\"fab\" href=\"teacher-batches.html\" title=\"New Batch\">\n<svg fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-width=\"2.5\" viewbox=\"0 0 24 24\"><line x1=\"12\" x2=\"12\" y1=\"5\" y2=\"19\"></line><line x1=\"5\" x2=\"19\" y1=\"12\" y2=\"12\"></line></svg>\n</a>\n<nav class=\"bnav\">\n<div class=\"bni\">\n<a class=\"bna active\" href=\"teacher-dashboard.html\">\n<svg fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" viewbox=\"0 0 24 24\"><path d=\"M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z\"></path><polyline points=\"9 22 9 12 15 12 15 22\"></polyline></svg>\n            Home\n        </a>\n<a class=\"bna\" href=\"teacher-batches.html\">\n<svg fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" viewbox=\"0 0 24 24\"><rect height=\"14\" rx=\"2\" width=\"20\" x=\"2\" y=\"7\"></rect><path d=\"M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2\"></path></svg>\n            Batches\n        </a>\n<a class=\"bna\" href=\"teacher-notices.html\">\n<svg fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" viewbox=\"0 0 24 24\"><path d=\"M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9\"></path><path d=\"M13.73 21a2 2 0 0 1-3.46 0\"></path></svg>\n            Notices\n        </a>\n<a class=\"bna\" href=\"attendance.html\">\n<svg fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" viewbox=\"0 0 24 24\"><path d=\"M4 19h16\"></path><path d=\"M7 15l3 3 7-8\"></path></svg>\n            Attendance\n        </a>\n<a class=\"bna\" href=\"teacher-results.html\">\n<svg fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" viewbox=\"0 0 24 24\"><path d=\"M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z\"></path><polyline points=\"14 2 14 8 20 8\"></polyline></svg>\n            Results\n        </a>\n<a class=\"bna\" href=\"teacher-profile.html\">\n<svg fill=\"none\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" viewbox=\"0 0 24 24\"><circle cx=\"12\" cy=\"8\" r=\"4\"></circle><path d=\"M4 20c0-4 3.6-7 8-7s8 3 8 7\"></path></svg>\n            Profile\n        </a>\n</div>\n</nav>"
  };

  const PAGE_META = {
    "student-dashboard.html": { layout: "student", title: "Dashboard | EduCoffee" },
    "student-notices.html": { layout: "student", title: "Notices | EduCoffee" },
    "student-results.html": { layout: "student", title: "Results | EduCoffee" },
    "student-profile.html": { layout: "student", title: "Profile | EduCoffee" },
    "teacher-dashboard.html": { layout: "teacher", title: "Teacher Dashboard | EduCoffee" },
    "teacher-batches.html": { layout: "teacher", title: "Batches | EduCoffee" },
    "teacher-students.html": { layout: "teacher", title: "Students | EduCoffee" },
    "teacher-notices.html": { layout: "teacher", title: "Teacher Notices | EduCoffee" },
    "attendance.html": { layout: "teacher", title: "Attendance Panel | EduCoffee" },
    "teacher-results.html": { layout: "teacher", title: "Teacher Results | EduCoffee" },
    "teacher-profile.html": { layout: "teacher", title: "Teacher Profile | EduCoffee" },
  };

  function currentFile() {
    const p = location.pathname.split("/").pop();
    return p || "student-dashboard.html";
  }

  function getCurrentSession() {
    if (typeof window.decodeJwtPayload === "function") {
      const jwtToken = localStorage.getItem("educoffee_token");
      const payload = jwtToken && window.decodeJwtPayload(jwtToken);
      if (payload && payload.sub) {
        return { id: payload.sub, role: payload.role || "", name: payload.name || "", email: "", token: jwtToken };
      }
    }
    const role =
      localStorage.getItem("current_user_role") ||
      localStorage.getItem("userRole") ||
      sessionStorage.getItem("current_user_role") ||
      sessionStorage.getItem("userRole") ||
      "";

    const id =
      localStorage.getItem("current_userid") ||
      localStorage.getItem("current_user_id") ||
      localStorage.getItem("userId") ||
      localStorage.getItem("user_id") ||
      sessionStorage.getItem("current_userid") ||
      sessionStorage.getItem("current_user_id") ||
      sessionStorage.getItem("userId") ||
      sessionStorage.getItem("user_id") ||
      "";

    const name =
      localStorage.getItem("current_user_name") ||
      localStorage.getItem("userName") ||
      sessionStorage.getItem("current_user_name") ||
      sessionStorage.getItem("userName") ||
      "";

    const email =
      localStorage.getItem("current_user_email") ||
      localStorage.getItem("userEmail") ||
      sessionStorage.getItem("current_user_email") ||
      sessionStorage.getItem("userEmail") ||
      "";

    const token =
      localStorage.getItem("access_token") ||
      localStorage.getItem("token") ||
      sessionStorage.getItem("access_token") ||
      sessionStorage.getItem("token") ||
      "";

    if (!id || !role) return null;
    return { id, role, name, email, token };
  }

  function doLogout() {
    if (typeof window.clearToken === "function") window.clearToken();
    [
      "loggedin",
      "current_userid",
      "current_user_id",
      "current_user_role",
      "current_user_name",
      "current_user_email",
      "userId",
      "userRole",
      "userName",
      "userEmail",
      "access_token",
      "token",
    ].forEach((k) => {
      localStorage.removeItem(k);
      sessionStorage.removeItem(k);
    });
    window.location.href = "auth.html";
  }

  function insertShell() {
    const meta = PAGE_META[currentFile()];
    if (!meta) return;
    const layout = meta.layout;
    const shellHtml = SHELLS[layout];
    if (!shellHtml) return;

    const placeholder = document.getElementById("ec-shell");
    if (!placeholder) return;

    const template = document.createElement("template");
    template.innerHTML = shellHtml.trim();
    placeholder.replaceWith(template.content.cloneNode(true));

    if (layout === "teacher") {
      const avatar = document.querySelector(".sidebar .uav");
      const name = document.querySelector(".sidebar .un");
      const fab = document.querySelector(".fab");
      if (avatar) avatar.id = "sidebarAvatar";
      if (name) name.id = "sidebarName";
      if (fab) fab.id = "ecTeacherFab";

      if (!document.getElementById("ec-shell-fixes")) {
        const style = document.createElement("style");
        style.id = "ec-shell-fixes";
        style.textContent = `
          #ecTeacherFab { display: none; }
          @media (max-width: 768px) {
            #ecTeacherFab {
              position: fixed; right: 20px; bottom: 80px; z-index: 150;
              display: flex; align-items: center; justify-content: center;
              width: 54px; height: 54px; border-radius: 50%;
              color: #fff; background: #3e2723; text-decoration: none;
              box-shadow: 0 8px 25px rgba(62,39,35,.3);
            }
            #ecTeacherFab svg { width: 24px; height: 24px; }
          }
        `;
        document.head.appendChild(style);
      }
    }

    if (layout === "student" && !document.getElementById("ec-student-shell-fixes")) {
      const style = document.createElement("style");
      style.id = "ec-student-shell-fixes";
      style.textContent = `
        .sidebar .user-chip { cursor: pointer; }
        .sidebar .user-avatar {
          width: 34px; height: 34px; border-radius: 10px; flex-shrink: 0;
          display: flex; align-items: center; justify-content: center;
          color: #fff; background: var(--caramel, #c68642);
          font-size: .85rem; font-weight: 700;
        }
        .sidebar .logout-btn {
          appearance: none; display: flex; align-items: center; justify-content: center;
          padding: 4px; border: 0; border-radius: 6px; cursor: pointer;
          color: rgba(255,255,255,.5); background: transparent;
          transition: color .2s;
        }
        .sidebar .logout-btn:hover { color: #fff; }
      `;
      document.head.appendChild(style);
    }

    if (meta.title) document.title = meta.title;

    const fname = currentFile();
    if (layout === "student") {
      document.querySelectorAll(".sidebar .nav-link, .bottom-nav .bnav-item").forEach((a) => {
        const href = a.getAttribute("href") || "";
        a.classList.toggle("active", href.includes(fname));
      });
    } else if (layout === "teacher") {
      document.querySelectorAll(".sidebar .nl, .bnav .bna").forEach((a) => {
        const href = a.getAttribute("href") || "";
        a.classList.toggle("active", href.includes(fname));
      });
    }
  }

  function ensureAdModalStyles() {
    if (document.getElementById("ec-ad-modal-style")) return;
    const style = document.createElement("style");
    style.id = "ec-ad-modal-style";
    style.textContent = `
      #ec-ad-modal {
        position: fixed; inset: 0; z-index: 2000;
        display: none; align-items: center; justify-content: center;
        padding: 20px; background: rgba(62,39,35,.45);
      }
      #ec-ad-modal.ec-ad-open { display: flex; }
      #ec-ad-dialog {
        position: relative; width: min(460px, calc(100vw - 32px));
        background: var(--card, #fffaf3); color: var(--text, #2d241e);
        border-radius: 18px; border: 1px solid var(--border, #eadfd6);
        box-shadow: 0 18px 55px rgba(62,39,35,.28);
        padding: 20px; overflow: hidden;
      }
      #ec-ad-dialog .ec-ad-close {
        position: absolute; right: 14px; top: 14px;
        width: 34px; height: 34px; border-radius: 50%; border: 0;
        background: rgba(62,39,35,.08); color: var(--coffee, #3e2723);
        font-size: 22px; line-height: 1; cursor: pointer;
      }
      #ec-ad-image-wrap { display: flex; align-items: center; justify-content: center; margin-bottom: 14px; }
      #ec-ad-image-wrap img { width: 100%; max-height: 190px; object-fit: cover; border-radius: 12px; border: 1px solid var(--border, #eadfd6); background: #fff; }
      #ec-ad-title { font: 700 1.08rem 'DM Serif Display', serif; color: var(--coffee, #3e2723); margin-bottom: 7px; }
      #ec-ad-body { font: 500 .88rem 'DM Sans', sans-serif; color: var(--muted, #786b64); line-height: 1.55; margin-bottom: 14px; }
      #ec-ad-continue { display: block; width: auto; min-width: 96px; margin-left: auto; border: 0; border-radius: 9px; padding: 9px 15px; background: var(--coffee, #3e2723); color: #fff; font: 700 .82rem 'DM Sans', sans-serif; cursor: pointer; }
      @media (max-width: 600px) { #ec-ad-dialog { padding: 18px; } }
    `;
    document.head.appendChild(style);
  }

  function ensureAdModal() {
    ensureAdModalStyles();
    let modal = document.getElementById("ec-ad-modal");
    if (modal) return modal;

    modal = document.createElement("div");
    modal.id = "ec-ad-modal";
    modal.innerHTML = `
      <div id="ec-ad-dialog">
        <button class="ec-ad-close" id="ec-ad-close" aria-label="Close">×</button>
        <div id="ec-ad-image-wrap" class="ec-ad-image-wrap"></div>
        <div id="ec-ad-content">
          <div id="ec-ad-title" class="ec-ad-title"></div>
          <div id="ec-ad-body" class="ec-ad-body"></div>
          <button id="ec-ad-continue" class="ec-ad-continue">Close</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);
    modal.querySelector("#ec-ad-close").addEventListener("click", () => closeAdModal(modal));
    modal.querySelector("#ec-ad-continue").addEventListener("click", () => closeAdModal(modal));
    return modal;
  }

  function closeAdModal(modal) {
    if (!modal) return;
    const adId = modal.dataset.adId;
    if (adId && typeof MarkAdSeen === "function") {
      MarkAdSeen(adId).catch(() => {});
    }
    modal.classList.remove("ec-ad-open");
    modal.dataset.adId = "";
  }

  async function showActiveAdPopup() {
    try {
      const session = typeof getCurrentSession === "function" ? getCurrentSession() : null;
      if (!session || !session.token) {
        console.log("[ad-popup] no session/token");
        return;
      }
      if (typeof GetActiveAds !== "function") {
        console.log("[ad-popup] GetActiveAds not available");
        return;
      }

      console.log("[ad-popup] fetching /ads/active");
      const ads = await GetActiveAds();
      console.log("[ad-popup] raw ads", ads);
      if (!Array.isArray(ads) || ads.length === 0) {
        console.log("[ad-popup] no active ads returned");
        return;
      }

      const ad = ads[0];
      const modal = ensureAdModal();
      modal.dataset.adId = ad.id || "";

      const imageWrap = modal.querySelector("#ec-ad-image-wrap");
      const title = modal.querySelector("#ec-ad-title");
      const body = modal.querySelector("#ec-ad-body");
      imageWrap.innerHTML = ad.image_url ? `<img src="${ad.image_url}" alt="${(ad.title || "Ad").replace(/</g, "&lt;")}" />` : "";
      title.textContent = ad.title || "Offer from EduCoffee";
      body.textContent = ad.body || "";

      modal.classList.add("ec-ad-open");
      console.log("[ad-popup] opened", ad);
    } catch (e) {
      console.log("[ad-popup] error", e?.message || e);
    }
  }

  function initNow() {
    insertShell();
    showActiveAdPopup();
  }

  function ensurePageLoader() {
    let loader = document.getElementById("ec-page-loader");
    if (loader) return loader;

    if (!document.getElementById("ec-page-loader-style")) {
      const style = document.createElement("style");
      style.id = "ec-page-loader-style";
      style.textContent = `
        #ec-page-loader {
          position: fixed; inset: 0; z-index: 9999; display: flex;
          align-items: center; justify-content: center;
          background: rgba(253,251,247,.94); backdrop-filter: blur(5px);
          opacity: 1; transition: opacity .25s ease;
        }
        #ec-page-loader.ec-loader-hiding { opacity: 0; pointer-events: none; }
        .ec-loader-card { text-align: center; color: #3e2723; }
        .ec-loader-ring {
          width: 58px; height: 58px; margin: 0 auto 14px; border-radius: 50%;
          border: 4px solid rgba(198,134,66,.18); border-top-color: #c68642;
          animation: ecLoaderSpin .8s linear infinite;
        }
        .ec-loader-title { font: 700 .9rem 'DM Sans', sans-serif; }
        .ec-loader-sub { margin-top: 4px; color: #7d6e64; font: 500 .72rem 'DM Sans', sans-serif; }
        @keyframes ecLoaderSpin { to { transform: rotate(360deg); } }
        @media (prefers-reduced-motion: reduce) { .ec-loader-ring { animation-duration: 1.8s; } }
      `;
      document.head.appendChild(style);
    }

    loader = document.createElement("div");
    loader.id = "ec-page-loader";
    loader.setAttribute("role", "status");
    loader.setAttribute("aria-live", "polite");
    loader.innerHTML = `<div class="ec-loader-card"><div class="ec-loader-ring"></div><div class="ec-loader-title">Loading EduCoffee…</div><div class="ec-loader-sub">Getting everything ready</div></div>`;
    document.body.appendChild(loader);
    return loader;
  }

  function showPageLoading(message = "Loading EduCoffee…") {
    const loader = ensurePageLoader();
    const title = loader.querySelector(".ec-loader-title");
    if (title) title.textContent = message;
    loader.classList.remove("ec-loader-hiding");
  }

  function hidePageLoading() {
    const loader = document.getElementById("ec-page-loader");
    if (!loader) return;
    loader.classList.add("ec-loader-hiding");
    setTimeout(() => loader.remove(), 260);
  }

  window.getCurrentSession = getCurrentSession;
  window.doLogout = doLogout;
  window.showPageLoading = showPageLoading;
  window.hidePageLoading = hidePageLoading;
  window.showActiveAdPopup = showActiveAdPopup;

  window.toggleSidebar = function () {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("mobileOverlay");
    if (!sidebar) return;
    sidebar.classList.add("mobile-open");
    if (overlay) overlay.classList.add("open");
  };
  window.closeSidebar = function () {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("mobileOverlay");
    if (!sidebar) return;
    sidebar.classList.remove("mobile-open");
    if (overlay) overlay.classList.remove("open");
  };
  window.toggleSB = window.toggleSidebar;
  window.closeSB = window.closeSidebar;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initNow, { once: true });
  } else {
    initNow();
  }
})();
